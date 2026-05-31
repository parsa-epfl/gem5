# Copyright (c) 2019 ARM Limited
# All rights reserved.
#
# The license below extends only to copyright in the software and shall
# not be construed as granting a license to any other intellectual
# property including but not limited to intellectual property relating
# to a hardware implementation of the functionality of the software
# licensed hereunder.  You may use the software subject to the license
# terms below provided that you ensure that this notice is replicated
# unmodified and in its entirety in all distributions of the software,
# modified or unmodified, in source code or in binary form.
#
# Copyright (c) 2006-2007 The Regents of The University of Michigan
# Copyright (c) 2009 Advanced Micro Devices, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met: redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer;
# redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution;
# neither the name of the copyright holders nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import math
from pathlib import Path
import m5
from m5.objects import *
from m5.defines import buildEnv
from .Ruby import create_topology, create_directories
from .Ruby import send_evicts

#
# Declare caches used by the protocol
#
class L1Cache(RubyCache):
    dataAccessLatency = 1
    tagAccessLatency = 1

class L2Cache(RubyCache):
    dataAccessLatency = 20
    tagAccessLatency = 20


GEM5_UARCH_SUFFIX = "gem5_uarch"
LLC_RESTORE_STAGED = "llc_restore_addrs.txt"
MOESI_PRIVATE_OWNER_RESTORE_STAGED = (
    "moesi_single_private_data_writeable_restore.txt"
)
MOESI_PRIVATE_OWNER_L1D_RESTORE_TEMPLATE = (
    "moesi_l1d_single_private_data_writeable.core{core}.txt"
)
MOESI_PRIVATE_CLEAN_RESTORE_STAGED = (
    "moesi_single_private_data_clean_restore.txt"
)
MOESI_PRIVATE_CLEAN_L1D_RESTORE_TEMPLATE = (
    "moesi_l1d_single_private_data_clean.core{core}.txt"
)
MOESI_MULTI_PRIVATE_CLEAN_RESTORE_STAGED = (
    "moesi_multi_private_data_clean_restore.txt"
)
MOESI_MULTI_PRIVATE_CLEAN_NONLLC_RESTORE_STAGED = (
    "moesi_multi_private_data_clean_nonllc_restore.txt"
)
MOESI_MULTI_PRIVATE_CLEAN_L1D_RESTORE_TEMPLATE = (
    "moesi_l1d_multi_private_data_clean.core{core}.txt"
)
MOESI_PRIVATE_INSTRUCTION_ONLY_RESTORE_STAGED = (
    "moesi_private_instruction_only_restore.txt"
)
MOESI_PRIVATE_INSTRUCTION_ONLY_NONLLC_RESTORE_STAGED = (
    "moesi_private_instruction_only_nonllc_restore.txt"
)
MOESI_PRIVATE_INSTRUCTION_ONLY_L1I_RESTORE_TEMPLATE = (
    "moesi_l1i_private_instruction_only.core{core}.txt"
)


def discover_gem5_uarch_dir(restore_dir: Path):
    workload_dir = restore_dir.parent
    snapshot_name = restore_dir.name
    nested = workload_dir / snapshot_name / GEM5_UARCH_SUFFIX
    sibling = workload_dir / f"{snapshot_name}.{GEM5_UARCH_SUFFIX}"

    if nested.is_dir():
        return nested
    if sibling.is_dir():
        return sibling
    return nested


def discover_llc_restore_file(options):
    if not getattr(options, "restore_llc_state", False):
        return None

    if not getattr(options, "restore", None):
        m5.util.warn(
            "--restore-llc-state was set without --restore; "
            "skipping LLC warm-state import."
        )
        return None

    restore_dir = Path(options.restore).resolve()
    gem5_uarch_dir = discover_gem5_uarch_dir(restore_dir)
    target_path = gem5_uarch_dir / LLC_RESTORE_STAGED

    if not gem5_uarch_dir.is_dir():
        m5.util.warn(
            "Skipping LLC warm-state import; gem5_uarch directory is missing: "
            f"{gem5_uarch_dir}"
        )
        return None

    if not target_path.is_file():
        m5.util.warn(
            "Skipping LLC warm-state import; restore file is missing: "
            f"{target_path}"
        )
        return None

    return str(target_path)

def discover_moesi_private_owner_restore_file(options):
    if not getattr(options, "restore_l1d_state", False):
        return None

    if not getattr(options, "restore", None):
        m5.util.warn(
            "--restore-l1d-state was set without --restore; "
            "skipping MOESI private-owner warm-state import."
        )
        return None

    restore_dir = Path(options.restore).resolve()
    gem5_uarch_dir = discover_gem5_uarch_dir(restore_dir)
    target_path = gem5_uarch_dir / MOESI_PRIVATE_OWNER_RESTORE_STAGED

    if not gem5_uarch_dir.is_dir():
        m5.util.warn(
            "Skipping MOESI private-owner warm-state import; gem5_uarch "
            f"directory is missing: {gem5_uarch_dir}"
        )
        return None

    if not target_path.is_file():
        m5.util.warn(
            "Skipping MOESI private-owner warm-state import; restore file is "
            f"missing: {target_path}"
        )
        return None

    return str(target_path)


def discover_moesi_private_clean_restore_file(options):
    if not getattr(options, "restore_l1d_state", False):
        return None

    if not getattr(options, "restore", None):
        m5.util.warn(
            "--restore-l1d-state was set without --restore; "
            "skipping MOESI private-clean warm-state import."
        )
        return None

    restore_dir = Path(options.restore).resolve()
    gem5_uarch_dir = discover_gem5_uarch_dir(restore_dir)
    target_path = gem5_uarch_dir / MOESI_PRIVATE_CLEAN_RESTORE_STAGED

    if not gem5_uarch_dir.is_dir():
        m5.util.warn(
            "Skipping MOESI private-clean warm-state import; gem5_uarch "
            f"directory is missing: {gem5_uarch_dir}"
        )
        return None

    if not target_path.is_file():
        m5.util.warn(
            "Skipping MOESI private-clean warm-state import; restore file is "
            f"missing: {target_path}"
        )
        return None

    return str(target_path)


def discover_moesi_multi_private_clean_restore_file(options):
    if not getattr(options, "restore_l1d_state", False):
        return None

    if not getattr(options, "restore", None):
        m5.util.warn(
            "--restore-l1d-state was set without --restore; "
            "skipping MOESI multi-private clean warm-state import."
        )
        return None

    restore_dir = Path(options.restore).resolve()
    gem5_uarch_dir = discover_gem5_uarch_dir(restore_dir)
    target_path = gem5_uarch_dir / MOESI_MULTI_PRIVATE_CLEAN_RESTORE_STAGED

    if not gem5_uarch_dir.is_dir():
        m5.util.warn(
            "Skipping MOESI multi-private clean warm-state import; gem5_uarch "
            f"directory is missing: {gem5_uarch_dir}"
        )
        return None

    if not target_path.is_file():
        m5.util.warn(
            "Skipping MOESI multi-private clean warm-state import; "
            "restore file is "
            f"missing: {target_path}"
        )
        return None

    return str(target_path)


def discover_moesi_multi_private_clean_nonllc_restore_file(options):
    if not getattr(options, "restore_l1d_state", False):
        return None

    if not getattr(options, "restore", None):
        m5.util.warn(
            "--restore-l1d-state was set without --restore; "
            "skipping MOESI non-LLC multi-private clean warm-state import."
        )
        return None

    restore_dir = Path(options.restore).resolve()
    gem5_uarch_dir = discover_gem5_uarch_dir(restore_dir)
    target_path = (
        gem5_uarch_dir / MOESI_MULTI_PRIVATE_CLEAN_NONLLC_RESTORE_STAGED
    )

    if not gem5_uarch_dir.is_dir():
        m5.util.warn(
            "Skipping MOESI non-LLC multi-private clean warm-state import; "
            f"gem5_uarch directory is missing: {gem5_uarch_dir}"
        )
        return None

    if not target_path.is_file():
        m5.util.warn(
            "Skipping MOESI non-LLC multi-private clean warm-state import; "
            f"restore file is missing: {target_path}"
        )
        return None

    return str(target_path)


def discover_moesi_private_instruction_only_restore_file(options):
    if not getattr(options, "restore_l1i_state", False):
        return None

    if not getattr(options, "restore", None):
        m5.util.warn(
            "--restore-l1i-state was set without --restore; "
            "skipping MOESI private instruction-only warm-state import."
        )
        return None

    restore_dir = Path(options.restore).resolve()
    gem5_uarch_dir = discover_gem5_uarch_dir(restore_dir)
    target_path = (
        gem5_uarch_dir / MOESI_PRIVATE_INSTRUCTION_ONLY_RESTORE_STAGED
    )

    if not gem5_uarch_dir.is_dir():
        m5.util.warn(
            "Skipping MOESI private instruction-only warm-state import; "
            f"gem5_uarch directory is missing: {gem5_uarch_dir}"
        )
        return None

    if not target_path.is_file():
        m5.util.warn(
            "Skipping MOESI private instruction-only warm-state import; "
            f"restore file is missing: {target_path}"
        )
        return None

    return str(target_path)


def discover_moesi_private_instruction_only_nonllc_restore_file(options):
    if not getattr(options, "restore_l1i_state", False):
        return None

    if not getattr(options, "restore", None):
        m5.util.warn(
            "--restore-l1i-state was set without --restore; "
            "skipping MOESI non-LLC instruction-only warm-state import."
        )
        return None

    restore_dir = Path(options.restore).resolve()
    gem5_uarch_dir = discover_gem5_uarch_dir(restore_dir)
    target_path = (
        gem5_uarch_dir / MOESI_PRIVATE_INSTRUCTION_ONLY_NONLLC_RESTORE_STAGED
    )

    if not gem5_uarch_dir.is_dir():
        m5.util.warn(
            "Skipping MOESI non-LLC instruction-only warm-state import; "
            f"gem5_uarch directory is missing: {gem5_uarch_dir}"
        )
        return None

    if not target_path.is_file():
        m5.util.warn(
            "Skipping MOESI non-LLC instruction-only warm-state import; "
            f"restore file is missing: {target_path}"
        )
        return None

    return str(target_path)


def discover_moesi_l1d_restore_files(options):
    if not getattr(options, "restore_l1d_state", False):
        return {}

    if not getattr(options, "restore", None):
        m5.util.warn(
            "--restore-l1d-state was set without --restore; "
            "skipping MOESI private L1D warm-state import."
        )
        return {}

    restore_dir = Path(options.restore).resolve()
    gem5_uarch_dir = discover_gem5_uarch_dir(restore_dir)

    if not gem5_uarch_dir.is_dir():
        m5.util.warn(
            "Skipping MOESI private L1D warm-state import; gem5_uarch "
            f"directory is missing: {gem5_uarch_dir}"
        )
        return {}

    restore_files = {}
    for core in range(getattr(options, "num_cpus", 0)):
        target_path = gem5_uarch_dir / (
            MOESI_PRIVATE_OWNER_L1D_RESTORE_TEMPLATE.format(core=core)
        )
        if target_path.is_file():
            restore_files[core] = str(target_path)

    if not restore_files:
        m5.util.warn(
            "No MOESI private-owner L1D restore files were found in "
            f"{gem5_uarch_dir}. Running with cold private L1D state."
        )

    return restore_files


def discover_moesi_l1d_multi_clean_restore_files(options):
    if not getattr(options, "restore_l1d_state", False):
        return {}

    if not getattr(options, "restore", None):
        m5.util.warn(
            "--restore-l1d-state was set without --restore; "
            "skipping MOESI multi-private clean L1D warm-state import."
        )
        return {}

    restore_dir = Path(options.restore).resolve()
    gem5_uarch_dir = discover_gem5_uarch_dir(restore_dir)

    if not gem5_uarch_dir.is_dir():
        m5.util.warn(
            "Skipping MOESI multi-private clean L1D warm-state import; "
            "gem5_uarch "
            f"directory is missing: {gem5_uarch_dir}"
        )
        return {}

    restore_files = {}
    for core in range(getattr(options, "num_cpus", 0)):
        target_path = gem5_uarch_dir / (
            MOESI_MULTI_PRIVATE_CLEAN_L1D_RESTORE_TEMPLATE.format(core=core)
        )
        if target_path.is_file():
            restore_files[core] = str(target_path)

    if not restore_files:
        m5.util.warn(
            "No MOESI multi-private clean L1D restore files were found in "
            f"{gem5_uarch_dir}. Running without the multi-private clean slice."
        )

    return restore_files


def discover_moesi_l1i_instruction_restore_files(options):
    if not getattr(options, "restore_l1i_state", False):
        return {}

    if not getattr(options, "restore", None):
        m5.util.warn(
            "--restore-l1i-state was set without --restore; "
            "skipping MOESI private instruction-only L1I warm-state import."
        )
        return {}

    restore_dir = Path(options.restore).resolve()
    gem5_uarch_dir = discover_gem5_uarch_dir(restore_dir)

    if not gem5_uarch_dir.is_dir():
        m5.util.warn(
            "Skipping MOESI private instruction-only L1I warm-state import; "
            f"gem5_uarch directory is missing: {gem5_uarch_dir}"
        )
        return {}

    restore_files = {}
    for core in range(getattr(options, "num_cpus", 0)):
        target_path = gem5_uarch_dir / (
            MOESI_PRIVATE_INSTRUCTION_ONLY_L1I_RESTORE_TEMPLATE.format(
                core=core
            )
        )
        if target_path.is_file():
            restore_files[core] = str(target_path)

    if not restore_files:
        m5.util.warn(
            "No MOESI private instruction-only L1I restore files were found "
            f"in {gem5_uarch_dir}. Running without the instruction-only slice."
        )

    return restore_files


def discover_moesi_l1d_clean_restore_files(options):
    if not getattr(options, "restore_l1d_state", False):
        return {}

    if not getattr(options, "restore", None):
        m5.util.warn(
            "--restore-l1d-state was set without --restore; "
            "skipping MOESI clean private L1D warm-state import."
        )
        return {}

    restore_dir = Path(options.restore).resolve()
    gem5_uarch_dir = discover_gem5_uarch_dir(restore_dir)

    if not gem5_uarch_dir.is_dir():
        m5.util.warn(
            "Skipping MOESI clean private L1D warm-state import; gem5_uarch "
            f"directory is missing: {gem5_uarch_dir}"
        )
        return {}

    restore_files = {}
    for core in range(getattr(options, "num_cpus", 0)):
        target_path = gem5_uarch_dir / (
            MOESI_PRIVATE_CLEAN_L1D_RESTORE_TEMPLATE.format(core=core)
        )
        if target_path.is_file():
            restore_files[core] = str(target_path)

    if not restore_files:
        m5.util.warn(
            "No MOESI private-clean L1D restore files were found in "
            f"{gem5_uarch_dir}. Running with cold private L1D state."
        )

    return restore_files


def define_options(parser):
    parser.add_argument(
        "--observe-restored-nonllc-getx",
        action="store_true",
        help=(
            "Log when a warm-restored non-LLC private-sharer line reaches "
            "the L2 ILS->L1_GETX upgrade path."
        ),
    )
    parser.add_argument(
        "--fatal-on-restored-nonllc-getx",
        action="store_true",
        help=(
            "Abort when a warm-restored non-LLC private-sharer line reaches "
            "the L2 ILS->L1_GETX upgrade path."
        ),
    )


def create_system(options, full_system, system, dma_ports, bootmem,
                  ruby_system, cpus):

    if buildEnv['PROTOCOL'] != 'MOESI_CMP_directory':
        panic(
            "This script requires the MOESI_CMP_directory "
            "protocol to be built."
        )

    cpu_sequencers = []

    #
    # The ruby network creation expects the list of nodes in the system to be
    # consistent with the NetDest list. Therefore the L1 controller nodes
    # must be listed before the directory nodes and directory nodes before
    # DMA nodes, etc.
    #
    l1_cntrl_nodes = []
    l2_cntrl_nodes = []
    dma_cntrl_nodes = []

    #
    # Must create the individual controllers before the network to ensure the
    # controller constructors are called before the network constructor
    #
    block_size_bits = int(math.log(options.cacheline_size, 2))
    l1i_instruction_restore_files = (
        discover_moesi_l1i_instruction_restore_files(options)
    )
    l1d_restore_files = discover_moesi_l1d_restore_files(options)
    l1d_clean_restore_files = discover_moesi_l1d_clean_restore_files(options)
    l1d_multi_clean_restore_files = (
        discover_moesi_l1d_multi_clean_restore_files(options)
    )
    private_owner_restore_file = discover_moesi_private_owner_restore_file(
        options
    )
    private_clean_restore_file = discover_moesi_private_clean_restore_file(
        options
    )
    private_multi_clean_restore_file = (
        discover_moesi_multi_private_clean_restore_file(options)
    )
    private_multi_clean_nonllc_restore_file = (
        discover_moesi_multi_private_clean_nonllc_restore_file(options)
    )
    private_instruction_restore_file = (
        discover_moesi_private_instruction_only_restore_file(options)
    )
    private_instruction_nonllc_restore_file = (
        discover_moesi_private_instruction_only_nonllc_restore_file(options)
    )
    owner_restore_enabled = bool(private_owner_restore_file)
    if l1d_restore_files and not owner_restore_enabled:
        m5.util.fatal(
            "Found MOESI private-owner L1D restore files without the "
            "matching aggregate owner metadata file. Refusing to warm L1D "
            "owner state without L2/directory owner restore."
        )
    multi_clean_nonllc_directory_enabled = bool(
        private_multi_clean_nonllc_restore_file
    )
    instruction_nonllc_directory_enabled = bool(
        private_instruction_nonllc_restore_file
    )
    multi_clean_enabled = bool(private_multi_clean_restore_file)
    multi_clean_nonllc_enabled = bool(
        private_multi_clean_nonllc_restore_file
    )
    instruction_restore_enabled = bool(private_instruction_restore_file)
    instruction_nonllc_restore_enabled = bool(
        private_instruction_nonllc_restore_file
    )
    instruction_only_enabled = bool(
        instruction_restore_enabled or instruction_nonllc_restore_enabled
    )

    for i in range(options.num_cpus):
        #
        # First create the Ruby objects associated with this cpu
        #
        l1i_cache = L1Cache(size = options.l1i_size,
                            assoc = options.l1i_assoc,
                            start_index_bit = block_size_bits,
                            is_icache = True)
        l1d_cache = L1Cache(size = options.l1d_size,
                            assoc = options.l1d_assoc,
                            start_index_bit = block_size_bits,
                            is_icache = False)

        clk_domain = cpus[i].clk_domain

        l1_cntrl = L1Cache_Controller(version=i, L1Icache=l1i_cache,
                                      L1Dcache=l1d_cache,
                                      send_evictions=send_evicts(options),
                                      transitions_per_cycle=options.ports,
                                      clk_domain=clk_domain,
                                      ruby_system=ruby_system,
                                      restore_l1i_state=(
                                          i in l1i_instruction_restore_files
                                      ),
                                      l1i_restore_file=(
                                          l1i_instruction_restore_files.get(
                                              i, ""
                                          )
                                      ),
                                      restore_l1d_state=(
                                          owner_restore_enabled
                                          and i in l1d_restore_files
                                      ),
                                      l1d_restore_file=(
                                          l1d_restore_files.get(i, "")
                                          if owner_restore_enabled
                                          else ""
                                      ),
                                      restore_l1d_clean_state=(
                                          i in l1d_clean_restore_files
                                      ),
                                      l1d_clean_restore_file=(
                                          l1d_clean_restore_files.get(i, "")
                                      ),
                                      restore_l1d_multi_clean_state=(
                                          i in l1d_multi_clean_restore_files
                                      ),
                                      l1d_multi_clean_restore_file=(
                                          l1d_multi_clean_restore_files.get(
                                              i, ""
                                          )
                                      ))

        cpu_seq = RubySequencer(version=i,
                                dcache=l1d_cache, clk_domain=clk_domain,
                                ruby_system=ruby_system)

        l1_cntrl.sequencer = cpu_seq
        exec("ruby_system.l1_cntrl%d = l1_cntrl" % i)

        # Add controllers and sequencers to the appropriate lists
        cpu_sequencers.append(cpu_seq)
        l1_cntrl_nodes.append(l1_cntrl)

        # Connect the L1 controllers and the network
        l1_cntrl.mandatoryQueue = MessageBuffer()
        l1_cntrl.requestFromL1Cache = MessageBuffer()
        l1_cntrl.requestFromL1Cache.master = ruby_system.network.slave
        l1_cntrl.responseFromL1Cache = MessageBuffer()
        l1_cntrl.responseFromL1Cache.master = ruby_system.network.slave
        l1_cntrl.requestToL1Cache = MessageBuffer()
        l1_cntrl.requestToL1Cache.slave = ruby_system.network.master
        l1_cntrl.responseToL1Cache = MessageBuffer()
        l1_cntrl.responseToL1Cache.slave = ruby_system.network.master
        l1_cntrl.triggerQueue = MessageBuffer(ordered = True)


    # Create the L2s interleaved addr ranges
    l2_addr_ranges = []
    l2_bits = int(math.log(options.num_l2caches, 2))
    numa_bit = block_size_bits + l2_bits - 1
    restore_file = discover_llc_restore_file(options)
    if restore_file and options.num_l2caches != 1:
        m5.util.fatal(
            "--restore-llc-state currently supports only --num-l2caches=1; "
            "got %d L2 caches." % options.num_l2caches
        )
    if private_owner_restore_file and options.num_l2caches != 1:
        m5.util.fatal(
            "MOESI private-owner warm restore currently supports only "
            "--num-l2caches=1; got %d L2 caches." % options.num_l2caches
        )
    if private_clean_restore_file and not restore_file:
        m5.util.fatal(
            "MOESI private-clean warm restore requires --restore-llc-state "
            "so LLC-backed lines exist before local sharer metadata is added."
        )
    if private_clean_restore_file and options.num_l2caches != 1:
        m5.util.fatal(
            "MOESI private-clean warm restore currently supports only "
            "--num-l2caches=1; got %d L2 caches." % options.num_l2caches
        )
    if private_multi_clean_restore_file and not restore_file:
        m5.util.fatal(
            "MOESI multi-private clean warm restore requires "
            "--restore-llc-state so LLC-backed lines exist before local "
            "sharer metadata is added."
        )
    if (
        multi_clean_enabled or multi_clean_nonllc_enabled
    ) and options.num_l2caches != 1:
        m5.util.fatal(
            "MOESI multi-private clean warm restore currently supports only "
            "--num-l2caches=1; got %d L2 caches." % options.num_l2caches
        )
    if private_instruction_restore_file and not restore_file:
        m5.util.fatal(
            "MOESI private instruction-only warm restore requires "
            "--restore-llc-state so LLC-backed lines exist before local "
            "sharer metadata is added."
        )
    if instruction_only_enabled and options.num_l2caches != 1:
        m5.util.fatal(
            "MOESI private instruction-only warm restore currently supports "
            "only --num-l2caches=1; got %d L2 caches." % options.num_l2caches
        )

    sysranges = [] + system.mem_ranges
    if bootmem: sysranges.append(bootmem.range)
    for i in range(options.num_l2caches):
        ranges = []
        for r in sysranges:
            addr_range = AddrRange(r.start, size = r.size(),
                                    intlvHighBit = numa_bit,
                                    intlvBits = l2_bits,
                                    intlvMatch = i)
            ranges.append(addr_range)
        l2_addr_ranges.append(ranges)

    for i in range(options.num_l2caches):
        #
        # First create the Ruby objects associated with this cpu
        #
        l2_cache = L2Cache(size = options.l2_size,
                           assoc = options.l2_assoc,
                           start_index_bit = block_size_bits + l2_bits)

        restore_instruction_state_arg = (
            i == 0 and instruction_restore_enabled
        )
        private_instruction_restore_file_arg = (
            private_instruction_restore_file
            if restore_instruction_state_arg
            else ""
        )
        restore_instruction_nonllc_state_arg = (
            i == 0 and instruction_nonllc_restore_enabled
        )
        private_instruction_nonllc_restore_file_arg = (
            private_instruction_nonllc_restore_file
            if restore_instruction_nonllc_state_arg
            else ""
        )
        restore_multi_clean_nonllc_state_arg = (
            i == 0 and multi_clean_nonllc_enabled
        )
        private_multi_clean_nonllc_restore_file_arg = (
            private_multi_clean_nonllc_restore_file
            if restore_multi_clean_nonllc_state_arg
            else ""
        )

        l2_cntrl = L2Cache_Controller(version = i,
                                      L2cache = l2_cache,
                                      transitions_per_cycle = options.ports,
                                      ruby_system = ruby_system,
                                      addr_ranges = l2_addr_ranges[i],
                                      restore_llc_state=(
                                          i == 0 and bool(restore_file)
                                      ),
                                      llc_restore_file=(
                                          restore_file
                                          if i == 0 and restore_file
                                          else ""
                                      ),
                                      restore_private_owner_state=(
                                          i == 0
                                          and bool(private_owner_restore_file)
                                      ),
                                      private_owner_restore_file=(
                                          private_owner_restore_file
                                          if (
                                              i == 0
                                              and private_owner_restore_file
                                          )
                                          else ""
                                      ),
                                      restore_private_clean_state=(
                                          i == 0
                                          and bool(private_clean_restore_file)
                                      ),
                                      private_clean_restore_file=(
                                          private_clean_restore_file
                                          if (
                                              i == 0
                                              and private_clean_restore_file
                                          )
                                          else ""
                                      ),
                                      restore_private_multi_clean_state=(
                                          i == 0 and multi_clean_enabled
                                      ),
                                      private_multi_clean_restore_file=(
                                          private_multi_clean_restore_file
                                          if (i == 0 and multi_clean_enabled)
                                          else ""
                                      ))

        l2_cntrl.restore_private_instruction_state = (
            restore_instruction_state_arg
        )
        l2_cntrl.private_instruction_restore_file = (
            private_instruction_restore_file_arg
        )
        l2_cntrl.restore_private_instruction_nonllc_state = (
            restore_instruction_nonllc_state_arg
        )
        l2_cntrl.private_instruction_nonllc_restore_file = (
            private_instruction_nonllc_restore_file_arg
        )
        l2_cntrl.restore_private_multi_clean_nonllc_state = (
            restore_multi_clean_nonllc_state_arg
        )
        l2_cntrl.private_multi_clean_nonllc_restore_file = (
            private_multi_clean_nonllc_restore_file_arg
        )
        l2_cntrl.observe_restored_nonllc_getx = bool(
            getattr(options, "observe_restored_nonllc_getx", False)
        )
        l2_cntrl.fatal_on_restored_nonllc_getx = bool(
            getattr(options, "fatal_on_restored_nonllc_getx", False)
        )

        exec("ruby_system.l2_cntrl%d = l2_cntrl" % i)
        l2_cntrl_nodes.append(l2_cntrl)

        # Connect the L2 controllers and the network
        l2_cntrl.GlobalRequestFromL2Cache = MessageBuffer()
        l2_cntrl.GlobalRequestFromL2Cache.master = ruby_system.network.slave
        l2_cntrl.L1RequestFromL2Cache = MessageBuffer()
        l2_cntrl.L1RequestFromL2Cache.master = ruby_system.network.slave
        l2_cntrl.responseFromL2Cache = MessageBuffer()
        l2_cntrl.responseFromL2Cache.master = ruby_system.network.slave

        l2_cntrl.GlobalRequestToL2Cache = MessageBuffer()
        l2_cntrl.GlobalRequestToL2Cache.slave = ruby_system.network.master
        l2_cntrl.L1RequestToL2Cache = MessageBuffer()
        l2_cntrl.L1RequestToL2Cache.slave = ruby_system.network.master
        l2_cntrl.responseToL2Cache = MessageBuffer()
        l2_cntrl.responseToL2Cache.slave = ruby_system.network.master
        l2_cntrl.triggerQueue = MessageBuffer(ordered = True)

    # Run each of the ruby memory controllers at a ratio of the frequency of
    # the ruby system.
    # clk_divider value is a fix to pass regression.
    ruby_system.memctrl_clk_domain = DerivedClockDomain(
                                          clk_domain=ruby_system.clk_domain,
                                          clk_divider=3)


    mem_dir_cntrl_nodes, rom_dir_cntrl_node = create_directories(
        options, bootmem, ruby_system, system)
    dir_cntrl_nodes = mem_dir_cntrl_nodes[:]
    if rom_dir_cntrl_node is not None:
        dir_cntrl_nodes.append(rom_dir_cntrl_node)
    for dir_cntrl in dir_cntrl_nodes:
        dir_cntrl.restore_llc_state = bool(restore_file)
        dir_cntrl.llc_restore_file = restore_file if restore_file else ""
        dir_cntrl.restore_private_owner_state = bool(
            private_owner_restore_file
        )
        dir_cntrl.private_owner_restore_file = (
            private_owner_restore_file if private_owner_restore_file else ""
        )
        dir_cntrl.restore_private_multi_clean_nonllc_state = (
            multi_clean_nonllc_directory_enabled
        )
        dir_cntrl.private_multi_clean_nonllc_restore_file = (
            private_multi_clean_nonllc_restore_file
            if private_multi_clean_nonllc_restore_file
            else ""
        )
        dir_cntrl.restore_private_instruction_nonllc_state = (
            instruction_nonllc_directory_enabled
        )
        dir_cntrl.private_instruction_nonllc_restore_file = (
            private_instruction_nonllc_restore_file
            if private_instruction_nonllc_restore_file
            else ""
        )
        # Connect the directory controllers and the network
        dir_cntrl.requestToDir = MessageBuffer()
        dir_cntrl.requestToDir.slave = ruby_system.network.master
        dir_cntrl.responseToDir = MessageBuffer()
        dir_cntrl.responseToDir.slave = ruby_system.network.master
        dir_cntrl.responseFromDir = MessageBuffer()
        dir_cntrl.responseFromDir.master = ruby_system.network.slave
        dir_cntrl.forwardFromDir = MessageBuffer()
        dir_cntrl.forwardFromDir.master = ruby_system.network.slave
        dir_cntrl.requestToMemory = MessageBuffer()
        dir_cntrl.responseFromMemory = MessageBuffer()
        dir_cntrl.triggerQueue = MessageBuffer(ordered = True)


    for i, dma_port in enumerate(dma_ports):
        #
        # Create the Ruby objects associated with the dma controller
        #
        dma_seq = DMASequencer(version = i,
                               ruby_system = ruby_system,
                               slave = dma_port)

        dma_cntrl = DMA_Controller(version = i,
                                   dma_sequencer = dma_seq,
                                   transitions_per_cycle = options.ports,
                                   ruby_system = ruby_system)

        exec("ruby_system.dma_cntrl%d = dma_cntrl" % i)
        dma_cntrl_nodes.append(dma_cntrl)

        # Connect the dma controller to the network
        dma_cntrl.mandatoryQueue = MessageBuffer()
        dma_cntrl.responseFromDir = MessageBuffer()
        dma_cntrl.responseFromDir.slave = ruby_system.network.master
        dma_cntrl.reqToDir = MessageBuffer()
        dma_cntrl.reqToDir.master = ruby_system.network.slave
        dma_cntrl.respToDir = MessageBuffer()
        dma_cntrl.respToDir.master = ruby_system.network.slave
        dma_cntrl.triggerQueue = MessageBuffer(ordered = True)


    all_cntrls = l1_cntrl_nodes + \
                 l2_cntrl_nodes + \
                 dir_cntrl_nodes + \
                 dma_cntrl_nodes

    # Create the io controller and the sequencer
    if full_system:
        io_seq = DMASequencer(version=len(dma_ports), ruby_system=ruby_system)
        ruby_system._io_port = io_seq
        io_controller = DMA_Controller(version = len(dma_ports),
                                       dma_sequencer = io_seq,
                                       ruby_system = ruby_system)
        ruby_system.io_controller = io_controller

        # Connect the dma controller to the network
        io_controller.mandatoryQueue = MessageBuffer()
        io_controller.responseFromDir = MessageBuffer()
        io_controller.responseFromDir.slave = ruby_system.network.master
        io_controller.reqToDir = MessageBuffer()
        io_controller.reqToDir.master = ruby_system.network.slave
        io_controller.respToDir = MessageBuffer()
        io_controller.respToDir.master = ruby_system.network.slave
        io_controller.triggerQueue = MessageBuffer(ordered = True)

        all_cntrls = all_cntrls + [io_controller]

    ruby_system.network.number_of_virtual_networks = 3
    topology = create_topology(all_cntrls, options)
    return (cpu_sequencers, mem_dir_cntrl_nodes, topology)
