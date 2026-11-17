#include <std_include.hpp>
#include "console.hpp"

#include "memory.hpp"

#include "game/game.hpp"

#include <utils/hook.hpp>


namespace memory
{
	namespace
	{
		constexpr auto mem_low_size = 0x80000000ull * 2; // default: 0x80000000
		constexpr auto mem_high_size = 0x80000000ull * 2; // default: 0x80000000

		// Keep stock low/high script offsets. Campaign bytecode is linked in HIGH.
		constexpr auto script_mem_low_size = 0x100000ull;
		constexpr auto script_mem_high_size = 0x100000ull + custom_script_mem_size;

		constexpr auto phys_mem_low_size = 0x700000000ull;
		constexpr auto phys_mem_high_size = 0x300000000ull;

		constexpr auto pmem_alloc_size =
			mem_low_size +
			mem_high_size +
			script_mem_low_size +
			script_mem_high_size +
			phys_mem_low_size +
			phys_mem_high_size;

		constexpr auto mem_low_buf = 0;
		constexpr auto mem_high_buf = mem_low_buf + mem_low_size;

		constexpr auto script_mem_low_buf = mem_high_buf + mem_high_size;
		constexpr auto script_mem_high_buf = script_mem_low_buf + script_mem_low_size;

		constexpr auto phys_mem_low_buf = script_mem_high_buf + script_mem_high_size;
		constexpr auto phys_mem_high_buf = phys_mem_low_buf + phys_mem_low_size;

		constexpr auto stream_mem_size = 0x2000000ull;

		void pmem_init()
		{
			const auto size = pmem_alloc_size;
			const auto allocated_buffer = VirtualAlloc(NULL, size, MEM_RESERVE, PAGE_READWRITE);
			auto buffer = static_cast<unsigned char*>(allocated_buffer);
			if (!buffer) throw std::runtime_error("GFL VR: could not reserve H1 asset address space");
			const auto stream = static_cast<unsigned char*>(VirtualAlloc(nullptr, stream_mem_size,
				MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE));
			if (!stream)
			{
				VirtualFree(buffer, 0, MEM_RELEASE);
				throw std::runtime_error("GFL VR: could not allocate the 32 MiB H1 stream buffer");
			}
			*game::pmem_size = size;
			*game::pmem_buffer = buffer;

			std::memset(game::g_mem, 0, sizeof(*game::g_mem));

			game::g_mem->prim[game::PHYS_ALLOC_LOW].buf = buffer + mem_low_buf;
			game::g_mem->prim[game::PHYS_ALLOC_LOW].pos = mem_low_size;
			game::g_mem->prim[game::PHYS_ALLOC_HIGH].buf = buffer + mem_high_buf;
			game::g_mem->prim[game::PHYS_ALLOC_HIGH].pos = mem_high_size;

			game::g_mem->prim[game::PHYS_ALLOC_LOW].unk1 = 0;
			game::g_mem->prim[game::PHYS_ALLOC_HIGH].unk1 = 0;

			std::memset(game::g_scriptmem, 0, sizeof(*game::g_scriptmem));

			game::g_scriptmem->prim[game::PHYS_ALLOC_LOW].buf = buffer + script_mem_low_buf;
			game::g_scriptmem->prim[game::PHYS_ALLOC_LOW].pos = script_mem_low_size;
			game::g_scriptmem->prim[game::PHYS_ALLOC_HIGH].buf = buffer + script_mem_high_buf;
			game::g_scriptmem->prim[game::PHYS_ALLOC_HIGH].pos = script_mem_high_size;

			game::g_scriptmem->prim[game::PHYS_ALLOC_LOW].unk1 = 0;
			game::g_scriptmem->prim[game::PHYS_ALLOC_HIGH].unk1 = 0;

			std::memset(game::g_physmem, 0, sizeof(*game::g_physmem));

			game::g_physmem->prim[game::PHYS_ALLOC_LOW].buf = buffer + phys_mem_low_buf;
			game::g_physmem->prim[game::PHYS_ALLOC_LOW].pos = phys_mem_low_size;
			game::g_physmem->prim[game::PHYS_ALLOC_HIGH].buf = buffer + phys_mem_high_buf;
			game::g_physmem->prim[game::PHYS_ALLOC_HIGH].pos = phys_mem_high_size;

			game::g_physmem->prim[game::PHYS_ALLOC_LOW].unk1 = 2;
			game::g_physmem->prim[game::PHYS_ALLOC_HIGH].unk1 = 2;

			*game::stream_size = stream_mem_size;
			*game::stream_buffer = stream;
		}

		void pmem_init_stub()
		{
			pmem_init();
			console::info("[GFL VR] H1 script arenas initialized: low=%llu MiB, high=%llu MiB.\n",
				script_mem_low_size >> 20, script_mem_high_size >> 20);
		}

		int memory_error(char* dest, int size, const char* format, ...)
		{
			char message[2048]{};
			va_list args;
			va_start(args, format);
			_vsnprintf_s(message, sizeof(message), _TRUNCATE, format, args);
			va_end(args);
			console::error("[GFL VR] H1 memory error: %s\n", message);
			return utils::hook::invoke<int>(0x140429200, dest, size, "%s", message);
		}
	}

	void install_gfl_hooks()
	{
		constexpr uintptr_t init_call = 0x14038639C;
		constexpr uintptr_t error_call = 0x140457BC9;
		constexpr uintptr_t script_limit = 0x140420252;
		uint32_t stock_limit;
		std::memcpy(&stock_limit, reinterpret_cast<const void*>(script_limit), sizeof(stock_limit));
		if (*reinterpret_cast<const uint8_t*>(init_call) != 0xe8 ||
			*reinterpret_cast<const uint8_t*>(error_call) != 0xe8 ||
			utils::hook::follow_branch(reinterpret_cast<void*>(error_call)) != reinterpret_cast<void*>(0x140429200) ||
			(stock_limit != 0x200000 && stock_limit != 0x100000))
			throw std::runtime_error("GFL VR: unexpected H1 memory initialization code");

		utils::hook::set<uint32_t>(script_limit, static_cast<uint32_t>(script_mem_low_size + script_mem_high_size));
		utils::hook::call(init_call, pmem_init_stub);
		utils::hook::call(error_call, memory_error);
	}
}
