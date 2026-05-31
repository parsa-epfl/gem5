# -*- mode:python -*-

# Copyright (c) 2024 ARM Limited
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

from m5.SimObject import SimObject
from m5.params import *
from m5.objects.ArmTLB import ArmTLB

class ArmVATranslator(SimObject):
    type = 'ArmVATranslator'
    cxx_class = 'gem5::ArmISA::VATranslator'
    cxx_header = 'arch/arm/va_translator.hh'

    cpu = Param.BaseCPU("CPU whose ThreadContext is used for translation")
    itb = Param.ArmTLB("Instruction TLB (ArmITB from cpu.mmu)")
    dtb = Param.ArmTLB("Data TLB (ArmDTB from cpu.mmu)")
    cpu_id = Param.Int(0, "Index of this CPU in the JSON MMU snapshot array")
    va_file = Param.String("", "Path to WormCacheQFlex MMU snapshot JSON file (e.g. mmus-0.json)")
    out_dir = Param.String("", "Output directory for mmu-cpuN.cpt checkpoint file (e.g. sim_outs)")
    exit_on_completion = Param.Bool(True,
        "Call exitSimLoop after all translations are done")
