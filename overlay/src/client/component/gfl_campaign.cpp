#include <std_include.hpp>
#include "loader/component_loader.hpp"
#include "game/game.hpp"
#include "console.hpp"
#include "command.hpp"
#include "scheduler.hpp"
#include "game/scripting/execution.hpp"
#include "game/scripting/array.hpp"
#include "gfl_campaign.hpp"
#include "memory.hpp"
#include "scripting.hpp"
#include <utils/flags.hpp>
#include <utils/io.hpp>
#include <utils/hook.hpp>

namespace gfl_campaign
{
    bool selected()
    {
        const auto mod = utils::flags::get_flag("mod");
        if (!mod) return false;
        return _stricmp(std::filesystem::path(*mod).lexically_normal().generic_string().c_str(), "mods/gfl") == 0;
    }

    namespace
    {
        constexpr auto custom_flags = game::DB_ZONE_COMMON | game::DB_ZONE_CUSTOM;

        // Same SP load boundary as Aurora H1-Mod. Use native H1 LZ4 zones so
        // the global decompressor and the VR renderer's streamed images stay native.
        void load_common(game::XZoneInfo* zones, unsigned count, game::DBSyncMode mode)
        {
            game::XZoneInfo assets{"gflvr_models", custom_flags, 0};
            game::DB_LoadXAssets(&assets, 1, game::DB_LOAD_ASYNC);
            game::DB_LoadXAssets(zones, count, mode);
            console::info("[GFL VR] Queued campaign models.\n");
        }

        void skip_companion_zones(utils::hook::assembler& a)
        {
            const auto custom = a.new_label();
            a.test(ebp, game::DB_ZONE_CUSTOM);
            a.jnz(custom);
            a.mov(r8d, 9);
            a.mov(rdx, 0x140782210);
            a.jmp(0x1401F4006);
            a.bind(custom);
            a.and_(ebp, ~game::DB_ZONE_CUSTOM);
            a.jmp(0x1401F4023);
        }

        struct script_entry
        {
            game::ScriptFile file{};
            std::string_view original_code;
        };

        std::string archive_bytes;
        std::unordered_map<std::string, script_entry> campaign;
        char* program{};
        unsigned program_size{};
        unsigned used{};

        std::string_view take(std::string_view& input, size_t count)
        {
            if (count > input.size()) throw std::runtime_error("GFL VR: truncated script archive");
            const auto part = input.substr(0, count);
            input.remove_prefix(count);
            return part;
        }

        unsigned read_size(std::string_view& input)
        {
            unsigned size;
            std::memcpy(&size, take(input, sizeof(size)).data(), sizeof(size));
            return size;
        }

        void index_campaign()
        {
            std::string_view input(archive_bytes);
            if (take(input, 4) != "GFL1") throw std::runtime_error("GFL VR: wrong script archive version");
            const auto count = read_size(input);
            if (!count || count > 4096) throw std::runtime_error("GFL VR: invalid script count");
            decltype(campaign) entries;
            size_t total = 0;
            for (unsigned i = 0; i < count; ++i)
            {
                const auto name_size = read_size(input);
                const auto record_size = read_size(input);
                const std::string name(take(input, name_size));
                auto record = take(input, record_size);
                if (take(record, 4) != std::string_view("GSC\0", 4))
                    throw std::runtime_error("GFL VR: invalid compiled script");
                const auto packed = read_size(record);
                const auto stack = read_size(record);
                const auto code = read_size(record);
                const auto compressed_stack = take(record, packed);
                const auto original_code = take(record, code);
                total += size_t(code) + 1;
                if (name.empty() || !code || !record.empty() || stack > INT_MAX ||
                    total > memory::custom_script_mem_size)
                    throw std::runtime_error("GFL VR: invalid script sizes");
                auto [it, inserted] = entries.try_emplace(name);
                if (!inserted) throw std::runtime_error("GFL VR: duplicate script key");
                it->second.file = {it->first.c_str(), int(packed), int(stack), int(code),
                    compressed_stack.data(), nullptr};
                it->second.original_code = original_code;
            }
            if (!input.empty()) throw std::runtime_error("GFL VR: trailing script archive data");
            campaign.swap(entries);
            program_size = static_cast<unsigned>(total);
        }

        game::XAssetHeader find_script(game::XAssetType type, const char* name, int allow_default)
        {
            if (campaign.empty()) index_campaign();
            const auto it = campaign.find(name);
            if (it == campaign.end()) return game::DB_FindXAssetHeader(type, name, allow_default);

            // The H1 linker rewrites operands in place. Give it fresh code in
            // the map's script arena, as H1-Mod does on each script reload.
            auto& entry = it->second;
            if (!entry.file.bytecode)
            {
                if (!program)
                    program = game::PMem_AllocFromSource_NoDebug(program_size, 4, game::PHYS_ALLOC_HIGH,
                        game::PMEM_SOURCE_SCRIPT);
                if (!program || entry.original_code.size() + 1 > program_size - used)
                    throw std::runtime_error("GFL VR: insufficient campaign bytecode space");
                auto* dest = program + used;
                std::memcpy(dest, entry.original_code.data(), entry.original_code.size());
                dest[entry.original_code.size()] = 0;
                used += static_cast<unsigned>(entry.original_code.size()) + 1;
                entry.file.bytecode = dest;
                console::info("[GFL VR] VM linking %s in campaign script memory\n", name);
            }
            game::XAssetHeader result{};
            result.scriptfile = &entry.file;
            return result;
        }

        int is_default(game::XAssetType type, const char* name)
        {
            if (campaign.contains(name)) return 0;
            return game::DB_IsXAssetDefault(type, name);
        }

        void release_campaign(bool free_scripts, bool post_shutdown)
        {
            if (!free_scripts || !post_shutdown) return;
            if (program)
                game::PMem_PopFromSource_NoDebug(program, program_size, 4, game::PHYS_ALLOC_HIGH,
                    game::PMEM_SOURCE_SCRIPT);
            program = nullptr;
            program_size = used = 0;
            campaign.clear();
        }

        void report_actors()
        {
            if (!game::SV_Loaded()) return;
            try
            {
                const auto actors = scripting::call<scripting::array>("getaiarray");
                for (int i = 0; i < actors.size(); ++i)
                {
                    const auto value = actors.get(i);
                    if (!value.is<scripting::entity>()) continue;
                    const auto actor = value.as<scripting::entity>();
                    const auto model = actor.get("model");
                    if (model.is<std::string>())
                        console::info("[GFL VR] Live actor %u model %s\n",
                            static_cast<unsigned>(actor.get_entity_reference().entnum),
                            model.as<std::string>().c_str());
                }
            }
            catch (const std::exception& error)
            {
                console::warn("[GFL VR] Actor query: %s\n", error.what());
            }
        }

        void require_call(std::uintptr_t address, std::uintptr_t target)
        {
            const auto site = reinterpret_cast<const unsigned char*>(address);
            std::int32_t distance;
            std::memcpy(&distance, site + 1, sizeof(distance));
            if (*site != 0xe8 || address + 5 + distance != target)
                throw std::runtime_error("GFL VR: unexpected H1 single-player call site");
        }
    }

    class component final : public component_interface
    {
    public:
        void post_unpack() override
        {
            if (!selected()) return;
            if (!std::filesystem::is_regular_file("zone/gflvr_models.ff") ||
                !utils::io::read_file("zone/gflvr_scripts.bin", &archive_bytes))
                throw std::runtime_error("GFL VR: missing campaign models or scripts");
            index_campaign();
            require_call(0x1405634AA, 0x1401F31E0);
            require_call(0x1403C7217, 0x1401F1120);
            require_call(0x1403C7227, 0x1401F25A0);
            // mov r8d,9; lea rdx,[rip+...] in DB's optional techsets name builder.
            const auto site = reinterpret_cast<const unsigned char*>(0x1401F3FF9);
            constexpr unsigned char prefix[]{0x41,0xb8,0x09,0,0,0,0x48,0x8d,0x15};
            std::int32_t displacement;
            std::memcpy(&displacement, site + 9, 4);
            if (std::memcmp(site, prefix, sizeof(prefix)) || 0x1401F4006 + displacement != 0x140782210)
                throw std::runtime_error("GFL VR: unexpected H1 zone builder");
            memory::install_gfl_hooks();
            utils::hook::jump(0x1401F3FF9, utils::hook::assemble(skip_companion_zones), true);
            utils::hook::call(0x1405634AA, load_common);
            utils::hook::call(0x1403C7217, find_script);
            utils::hook::call(0x1403C7227, is_default);
            scripting::on_shutdown(release_campaign);
            command::add("gfl_status", [] { scheduler::once(report_actors, scheduler::pipeline::server); });
            console::info("[GFL VR] H1 campaign loader installed.\n");
        }
    };
}

REGISTER_COMPONENT(gfl_campaign::component)
