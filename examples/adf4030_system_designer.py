import math, time
from math import ceil, sqrt

from adijif.plls.utils.adf4030_arch import (
    Aion_per_FPGA_cascade,
    Aion_per_FPGA_tree,
    Apollo_per_Aion_cascade,
    Apollo_per_Aion_tree,
    convert_sec_into_hms,
)


"""
Created on Thu Feb  6 10:37:14 2025

@author: PMinciu
This tool provides partitioning solutions for Apollo systems in the following
architectures:
    - cascade
    - tree
    - hybrid cascade - tree (i.e. hybrid notation)
    - hybrid tree - cascade (i.e hybrid2 notation)
Inputs: 
    N = how many Apollo devices are in the system
    N_Apollo = How many Apollo devices may be put on a Unit Board
    N_FPGA = How many FPGA devices may be put on a Unit Board. This determines 
             how many Apollo devices an FPGA manages
    f_SYSREF = Apollo SYSREF frequency expressed in MHz
    N_branch = desired number of branches in the hybrid tree - cascade architecture
Outputs:
-	NAion_UB_cascade/tree/hybrid/hybrid2 : 
        - how many Aion devices are on a Unit Board
-	NAion_per_FPGA_cascade/tree/hybrid/hybrid2[i], i=0,…, NFPGA-1: 
        - how many Aion devices are assigned per FPGA on a Unit Board
-	MaxAion_per_FPGA_cascade/tree/hybrid/hybrid2: 
        - the maximum number of Aion devices assigned per one FPGA on a Unit board
-	NApollo_per_Aion_cascade/tree/hybrid/hybrid2[i], 
        i=0,…, NAion_UB_cascade/tree/hybrid/hybrid2-1: 
        - how many Apollo devices are managed by each Aion on a Unit Board
-	MaxApollo_per_FPGA_cascade/tree/hybrid/hybrid2: 
        - the maximum number of Apollo devices assigned to one Aion on a Unit Board
-	NUB_cascade/tree/hybrid/hybrid2: 
        - the number of Unit Boards recommended in the system
-	NAion_system_cascade/tree/hybrid/hybrid2: 
        - the number of Aion devices in the system
-	tsync_UB: the time to synchronize all Apollo devices on a Unit Board
-	tsync_all_cascade/tree/hybrid/hybrid2: 
        - the time to synchronize all Apollo devices in the system
-	σalignment_cascade/tree/hybrid/hybrid2:  
        - One sigma alignment error between the first BSYNC channel of the 
        first Aion in the cascade and the last BSYNC channel of the last Aion
-	3σalignment_cascade/tree/hybrid/hybrid2: 
        - Three sigma alignment error between the first BSYNC channel of the 
        first Aion in the cascade and the last BSYNC channel of the last Aion
    
"""


# Introduce the inputs here:
# N = how many Apollo devices are in the system
N = 2912

# N_Apollo = How many Apollo devices may be put on a Unit Board
N_Apollo = 1

# N_FPGA = How many FPGA devices may be put on a Unit Board. This determines
#         how many Apollo devices an FPGA manages
N_FPGA = 1

# f_BSYNC = Apollo SYSREF frequency expressed in MHz
f_SYSREF = 9.765625

# the number of branches in the hybrid tree - cascade architecture
N_branch = 100


###############################################################################
# Timings given by Apollo team
###############################################################################
# Apollo boot timing (expressed in seconds)
t_Apollo_boot = 0.2

# Apollo initialization timing (expressed in seconds)
t_Apollo_cfg = 12.295

# Aion startup and configuration of BSYNC input/output channels duration (expressed in seconds)
t_Aion_cfg = 0.630

# Duration of Configuring MCS Init Cal and ADF4382 settings (expressed in seconds)
t_MCS_cfg = 0.746

# Aion - Apollo Time-of-Flight Measurement and offset compensation (expressed in seconds)
t_Aion_Apollo_tof0 = 1.911

# Aion - FPGA Time-of-Flight Measurement and offset compensation (expressed in seconds)
t_Aion_FPGA_tof0 = 6.873

# SYNC all BSYNC_OUT channels with BSYNC_IN Ref channel duration (expressed in seconds)
t_Aion_sync0 = 0.932

# Apollo internal SYSREF is aligned to the incoming external SYSREF duration
# (expressed in seconds)
t_Apollo_sync0 = 0.403

# SYSREF frequency for which these timings were obtained (expressed in MHz)
f_SYSREF0 = 9.765625

# we recalculate the timings function of the SYSREF frequency that will be used in the system
t_Aion_Apollo_tof = f_SYSREF * t_Aion_Apollo_tof0 / f_SYSREF0
t_Aion_FPGA_tof = f_SYSREF * t_Aion_FPGA_tof0 / f_SYSREF0
t_Aion_sync = f_SYSREF * t_Aion_sync0 / f_SYSREF0
t_Apollo_sync = f_SYSREF * t_Apollo_sync0 / f_SYSREF0


# create a postfix function of the time at which the file is created
exact_time = time.localtime()
if exact_time.tm_mon < 10:
    month = str("0") + str(exact_time.tm_mon)

if exact_time.tm_mday < 10:
    day = str("0") + str(exact_time.tm_mday)
else:
    day = str(exact_time.tm_mday)

postfix = str(exact_time.tm_year) + str(month) + str(day)


# create a file with the results of this program
root = "./"
filen = "tool_results" + "_" + str(postfix) + ".dat"
f = open(root + filen.split(".")[0] + ".dat", "w")


f.write("The number of Apollo devices in the system is: ")
f.write(str(N))
f.write("\n")

f.write("The number of Apollo devices on a Unit Board is: ")
f.write(str(N_Apollo))
f.write("\n")

f.write("The number of FPGA devices on a Unit Board is: ")
f.write(str(N_FPGA))
f.write("\n")

f.write("The Apollo SYSREF frequency is: ")
f.write(str(f_SYSREF))
f.write(" MHz")
f.write("\n")

f.write("The number of branches in the hybrid tree - cascade architecture is:")
f.write(str(N_branch))
f.write("\n")

###############################################################################
# Calculations for a Cascade Architecture
###############################################################################
f.write("----------------------------------------------------------------------")
f.write("\n")
f.write("This is the proposal for a cascade architecture")
f.write("\n")
f.write("----------------------------------------------------------------------")
f.write("\n")

# the number of Aion devices on a Unit Board is calculated
N_Aion_UB_cascade = ceil((N_Apollo - 7) / 8) + 1

f.write("     The number of Aion devices per Unit Board is : ")
f.write(str(N_Aion_UB_cascade))
f.write("\n")

# The number of Aion devices assigned to every FPGA on the Unit Board is calculated
(N_Aion_per_FPGA_cascade, Max_Aion_per_FPGA_cascade) = Aion_per_FPGA_cascade(
    N_Aion_UB_cascade, N_FPGA
)

for index in range(0, len(N_Aion_per_FPGA_cascade)):
    f.write("          FPGA[")
    f.write(str(index))
    f.write("] manages:")
    f.write(str(N_Aion_per_FPGA_cascade[index]))
    if N_Aion_per_FPGA_cascade[index] == 1:
        f.write(" Aion device")
    else:
        f.write(" Aion devices")
    f.write("\n")

if len(N_Aion_per_FPGA_cascade) < N_FPGA:
    if N_FPGA - len(N_Aion_per_FPGA_cascade) == 1:
        f.write("          One FPGA device does not manage any Aion")
    else:
        f.write("          ")
        f.write(str(N_FPGA - len(N_Aion_per_FPGA_cascade)))
        f.write(" FPGA devices do not manage any Aion")
        f.write("\n")

f.write("    The maximum number of Aion devices per FPGA on the Unit Board is: ")
f.write(str(Max_Aion_per_FPGA_cascade))
f.write("\n")

# the number of Apollo devices assigned per Aion is calculated
N_Apollo_per_Aion_cascade = Apollo_per_Aion_cascade(N_Apollo, N_Aion_UB_cascade)

# write the results in the output file
f.write("    The number of Apollo devices per Unit Board is: ")
f.write(str(N_Apollo))
f.write("\n")
for index in range(0, ceil((N_Apollo - 7) / 8) + 1):
    f.write("          Aion[")
    f.write(str(index))
    f.write("] manages:")
    f.write(str(N_Apollo_per_Aion_cascade[index]))
    f.write(" Apollo devices")
    f.write("\n")

# the maximum number of Apollo devices managed by one FPGA on a Unit Board is
# calculated
Max_Apollo_per_FPGA_cascade = 0
for index in range(0, N_FPGA):
    temp = 0
    for index2 in range(0, N_Aion_per_FPGA_cascade[index]):
        temp = temp + N_Apollo_per_Aion_cascade[index2]
    Max_Apollo_per_FPGA_cascade = max(Max_Apollo_per_FPGA_cascade, temp)

f.write("    The maximum number of Apollo devices per FPGA on the Unit Board is: ")
f.write(str(Max_Apollo_per_FPGA_cascade))
f.write("\n")

# the number of Unit Boards N_UB is calculated
N_UB_cascade = math.ceil(N / N_Apollo)

f.write("    The number of Unit Boards in the system is ")
f.write(str(N_UB_cascade))
f.write("\n")

# the total number of Aion devices in the system is:
N_Aion_system_cascade = N_UB_cascade * N_Aion_UB_cascade
f.write("    The number of Aion devices in the system is ")
f.write(str(N_Aion_system_cascade))
f.write("\n")


# to calculate the synchronization time of all devices on a Unit Board,
# we need to calculate some max values


# the synchronization time of all Apollo devices on a Unit Board in the cascade
# system is:
t_sync_UB_cascade = (
    t_Apollo_boot
    + Max_Apollo_per_FPGA_cascade * (t_Apollo_cfg + t_MCS_cfg + t_Apollo_sync)
    + Max_Aion_per_FPGA_cascade * (t_Aion_cfg + t_Aion_sync)
    + N_Apollo * t_Aion_Apollo_tof
    + N_FPGA * t_Aion_FPGA_tof
)

# Calculate the number of hours, minutes and seconds for t_sync_UB_cascade
time_hms = convert_sec_into_hms(t_sync_UB_cascade)

f.write("    The time to synchronize all Apollo devices on a Unit Board is: ")
f.write(str(round(t_sync_UB_cascade, 3)))
f.write(" seconds, that is: ")
f.write(str(time_hms))
f.write("\n")

# the time to synchronize all Unit Boards (i.e. all Apollo devices in the system) is:
t_sync_all_cascade = (
    t_Apollo_boot
    + Max_Apollo_per_FPGA_cascade * (t_Apollo_cfg + t_MCS_cfg + t_Apollo_sync)
    + Max_Aion_per_FPGA_cascade * (t_Aion_cfg + t_Aion_sync)
    + N_UB_cascade * (N_Apollo * t_Aion_FPGA_tof + N_FPGA * t_Aion_FPGA_tof)
)

# Calculate the number of hours, minutes and seconds for t_sync_all_cascade
time_hms = convert_sec_into_hms(t_sync_all_cascade)


f.write("    The time to synchronize all Apollo devices in the system is: ")
f.write(str(round(t_sync_all_cascade, 3)))
f.write(" seconds, that is: ")
f.write(str(time_hms))
f.write("\n")

# calculate the alignment error sigma distribution between the 1st BSYNC channel
# of the 1st Aion device in the cascade and the last BSYNC channel of the last
# Aion device in the cascade is sqrt(N_Aion_system_cascade)*2.36ps (2.36=10/3/sqrt2)
sigma_alignment_cascade = sqrt(N_Aion_system_cascade) * 10 / 3 / sqrt(2)
f.write("    One sigma alignment error between the first BSYNC channel of the ")
f.write(
    "first Aion in the cascade and \n        the last BSYNC channel of the last Aion"
)
f.write(" in the cascade is: ")
f.write(str(round(sigma_alignment_cascade, 3)))
f.write(" ps \n")

f.write("    Three sigma alignment error between the first BSYNC channel of the ")
f.write(
    "first Aion in the cascade and \n        the last BSYNC channel of the last Aion"
)
f.write(" in the cascade is: ")
f.write(str(round(3 * sigma_alignment_cascade, 3)))
f.write(" ps \n")


###############################################################################
# Calculations for a Tree Architecture
###############################################################################
f.write("----------------------------------------------------------------------")
f.write("\n")
f.write("This is the proposal for a tree architecture")
f.write("\n")
f.write("----------------------------------------------------------------------")
f.write("\n")

# the number of Aion devices on a Unit Board is calculated
N_Aion_UB_tree = ceil((N_Apollo - 8) / 9) + 1

f.write("     The number of Aion devices per Unit Board is : ")
f.write(str(N_Aion_UB_tree))
f.write("\n")

# The number of Aion devices assigned to every FPGA on the Unit Board is calculated
(N_Aion_per_FPGA_tree, Max_Aion_per_FPGA_tree) = Aion_per_FPGA_tree(
    N_Aion_UB_tree, N_FPGA
)

for index in range(0, len(N_Aion_per_FPGA_tree)):
    f.write("          FPGA[")
    f.write(str(index))
    f.write("] manages:")
    f.write(str(N_Aion_per_FPGA_tree[index]))
    if N_Aion_per_FPGA_tree[index] == 1:
        f.write(" Aion device")
    else:
        f.write(" Aion devices")
    f.write("\n")

if len(N_Aion_per_FPGA_tree) < N_FPGA:
    if N_FPGA - len(N_Aion_per_FPGA_tree) == 1:
        f.write("          One FPGA device does not manage any Aion")
    else:
        f.write("          ")
        f.write(str(N_FPGA - len(N_Aion_per_FPGA_tree)))
        f.write(" FPGA devices do not manage any Aion")
        f.write("\n")

f.write("    The maximum number of Aion devices per FPGA on the Unit Board is: ")
f.write(str(Max_Aion_per_FPGA_tree))
f.write("\n")

# the number of Apollo devices assigned per Aion is calculated
N_Apollo_per_Aion_tree = Apollo_per_Aion_tree(N_Apollo, N_Aion_UB_tree)

# write the results in the output file
f.write("    The number of Apollo devices per Unit Board is: ")
f.write(str(N_Apollo))
f.write("\n")
for index in range(0, ceil((N_Apollo - 8) / 9) + 1):
    f.write("          Aion[")
    f.write(str(index))
    f.write("] manages:")
    f.write(str(N_Apollo_per_Aion_tree[index]))
    f.write(" Apollo devices")
    f.write("\n")

# the maximum number of Apollo devices managed by one FPGA on a Unit Board is
# calculated
Max_Apollo_per_FPGA_tree = 0
for index in range(0, N_FPGA):
    temp = 0
    for index2 in range(0, N_Aion_per_FPGA_tree[index]):
        temp = temp + N_Apollo_per_Aion_tree[index2]
    Max_Apollo_per_FPGA_tree = max(Max_Apollo_per_FPGA_tree, temp)

f.write("    The maximum number of Apollo devices per FPGA on the Unit Board is: ")
f.write(str(Max_Apollo_per_FPGA_tree))
f.write("\n")

# the number of Unit Boards N_UB is calculated. It is equal to N_UB_cascade
N_UB_tree = math.ceil(N / N_Apollo)

f.write("    The number of Unit Boards in the system is ")
f.write(str(N_UB_tree))
f.write("\n")

# the number of Aion devices on the System Board is calculated
index = 0
N_Aion_SB_tree = 0
M_tree = []
# the first column of Aion tree consists in the Aion devices from the Unit Boards
M_tree.append(N_UB_tree * N_Aion_UB_tree)
while M_tree[index] > 1:
    number = math.ceil(M_tree[index] / 9)
    index += 1
    M_tree.append(number)
    N_Aion_SB_tree = N_Aion_SB_tree + M_tree[index]

f.write("    The number of Aion devices on a System Board is ")
f.write(str(N_Aion_SB_tree))
f.write("\n")

f.write("    The number of Aion devices per tree column is:")
f.write("\n")

f.write("        Tree Column number 0 has ")
f.write(str(M_tree[0]))
f.write(" Aion devices (all Unit Board devices)")
f.write("\n")


for index in range(1, len(M_tree)):
    if M_tree[index] == 1:
        f.write("        Tree Column number ")
        f.write(str(index))
        f.write(" has ")
        f.write(str(M_tree[index]))
        f.write(" Aion device \n")
    else:
        f.write("        Tree Column number ")
        f.write(str(index))
        f.write(" has ")
        f.write(str(M_tree[index]))
        f.write(" Aion devices \n")

# the total number of Aion devices in the system is:
N_Aion_system_tree = N_UB_tree * N_Aion_UB_tree + N_Aion_SB_tree
f.write(
    "    The number of Aion devices in the system (on the System Board and all Unit Boards) is "
)
f.write(str(N_Aion_system_tree))
f.write("\n")


# the synchronization time of all Apollo devices on a Unit Board in the tree
# system is:
t_sync_UB_tree = (
    t_Apollo_boot
    + Max_Apollo_per_FPGA_tree
    * (t_Apollo_cfg + t_MCS_cfg + t_Aion_Apollo_tof + t_Apollo_sync)
    + Max_Aion_per_FPGA_tree * (t_Aion_cfg + t_Aion_sync)
    + t_Aion_FPGA_tof
)

# Calculate the number of hours, minutes and seconds for t_sync_UB_tree
time_hms = convert_sec_into_hms(t_sync_UB_tree)

f.write("    The time to synchronize all Apollo devices on a Unit Board is: ")
f.write(str(round(t_sync_UB_tree, 3)))
f.write(" seconds, that is ")
f.write(str(time_hms))
f.write("\n")

# Calculate the synchronization time of all Aion devices on the System Board
t_sync_SB_tree = (
    N_Aion_SB_tree * (t_Aion_cfg + t_Aion_sync)
    + (N_Aion_system_tree - 1) * t_Aion_Apollo_tof
    + t_Aion_FPGA_tof
)

# Calculate the number of hours, minutes and seconds for t_sync_SB
time_hms = convert_sec_into_hms(t_sync_SB_tree)

f.write("    The time to synchronize all Aion devices on a System Board is: ")
f.write(str(round(t_sync_SB_tree, 3)))
f.write(" seconds, that is ")
f.write(str(time_hms))
f.write("\n")


# Calculate the total synchronization time of the system organized in a tree
t_sync_all_tree = t_sync_SB_tree + t_sync_UB_tree

# Calculate the number of hours, minutes and seconds for t_sync_all_tree
time_hms = convert_sec_into_hms(t_sync_all_tree)

f.write("    The time to synchronize all Apollo devices in the system is: ")
f.write(str(round(t_sync_all_tree, 3)))
f.write(" seconds, that is ")
f.write(str(time_hms))
f.write("\n")


# calculate the alignment error sigma distribution between the 1st Apollo device
# and the last one in the tree is sqrt(len(M_tree))*2.36ps (2.36=*10/2/sqrt(2))
sigma_alignment_tree = sqrt(len(M_tree)) * 10 / 3 / sqrt(2)
f.write("    One sigma alignment error between the first BSYNC channel of the ")
f.write("first Aion on the first tree column \n        and the BSYNC channels of the ")
f.write("Aion devices on the last tree column is: ")
f.write(str(round(sigma_alignment_tree, 3)))
f.write(" ps")
f.write("\n")

f.write("    Three sigma alignment error between the first BSYNC channel of the ")
f.write("first Aion on the first tree column \n        and the BSYNC channels of the ")
f.write("Aion devices on the last three column is: ")
f.write(str(round(3 * sigma_alignment_tree, 3)))
f.write(" ps")
f.write("\n")


###############################################################################
# Calculations for a Hybrid Cascade - Tree Architecture
###############################################################################
f.write("----------------------------------------------------------------------\n")
f.write("This is the proposal for a hybrid cascade - tree architecture \n")
f.write("----------------------------------------------------------------------\n")

# the number of Aion devices on a Unit Board is calculated
# It is the same as in the tree architecture
N_Aion_UB_hybrid = ceil((N_Apollo - 8) / 9) + 1

f.write("     The number of Aion devices per Unit Board is : ")
f.write(str(N_Aion_UB_hybrid))
f.write("\n")

# The number of Aion devices assigned to every FPGA on the Unit Board is calculated
(N_Aion_per_FPGA_hybrid, Max_Aion_per_FPGA_hybrid) = Aion_per_FPGA_tree(
    N_Aion_UB_hybrid, N_FPGA
)

for index in range(0, len(N_Aion_per_FPGA_hybrid)):
    f.write("          FPGA[")
    f.write(str(index))
    f.write("] manages:")
    f.write(str(N_Aion_per_FPGA_hybrid[index]))
    if N_Aion_per_FPGA_hybrid[index] == 1:
        f.write(" Aion device")
    else:
        f.write(" Aion devices")
    f.write("\n")

if len(N_Aion_per_FPGA_hybrid) < N_FPGA:
    if N_FPGA - len(N_Aion_per_FPGA_hybrid) == 1:
        f.write("          One FPGA device does not manage any Aion")
    else:
        f.write("          ")
        f.write(str(N_FPGA - len(N_Aion_per_FPGA_hybrid)))
        f.write(" FPGA devices do not manage any Aion")
        f.write("\n")

f.write("    The maximum number of Aion devices per FPGA on the Unit Board is: ")
f.write(str(Max_Aion_per_FPGA_hybrid))
f.write("\n")

# the number of Apollo devices assigned per Aion is calculated
N_Apollo_per_Aion_hybrid = Apollo_per_Aion_tree(N_Apollo, N_Aion_UB_hybrid)

# write the results in the output file
f.write("    The number of Apollo devices per Unit Board is: ")
f.write(str(N_Apollo))
f.write("\n")
for index in range(0, ceil((N_Apollo - 8) / 9) + 1):
    f.write("          Aion[")
    f.write(str(index))
    f.write("] manages:")
    f.write(str(N_Apollo_per_Aion_hybrid[index]))
    f.write(" Apollo devices")
    f.write("\n")

# the maximum number of Apollo devices managed by one FPGA on a Unit Board is
# calculated
Max_Apollo_per_FPGA_hybrid = 0
for index in range(0, N_FPGA):
    temp = 0
    for index2 in range(0, N_Aion_per_FPGA_hybrid[index]):
        temp = temp + N_Apollo_per_Aion_hybrid[index2]
    Max_Apollo_per_FPGA_hybrid = max(Max_Apollo_per_FPGA_hybrid, temp)

f.write("    The maximum number of Apollo devices per FPGA on the Unit Board is: ")
f.write(str(Max_Apollo_per_FPGA_hybrid))
f.write("\n")

# the number of Unit Boards N_UB is calculated. It is equal to N_UB_cascade
N_UB_hybrid = math.ceil(N / N_Apollo)

f.write("    The number of Unit Boards in the system is ")
f.write(str(N_UB_hybrid))
f.write("\n")


# the number of Aion devices on the System Board is calculated
N_Aion_SB_hybrid = math.ceil(N_UB_hybrid * N_Aion_UB_hybrid / 8)

f.write("    The number of Aion devices on a System Board is ")
f.write(str(N_Aion_SB_hybrid))
f.write("\n")


# the total number of Aion devices in the system is:
N_Aion_system_hybrid = N_UB_hybrid * N_Aion_UB_hybrid + N_Aion_SB_hybrid
f.write(
    "    The number of Aion devices in the system (on the System Board and all Unit Boards) is "
)
f.write(str(N_Aion_system_hybrid))
f.write("\n")


# the synchronization time of all Apollo devices on a Unit Board in the hybrid
# system is equal to the synchronization time of a Unit Board into a tree system:
t_sync_UB_hybrid = t_sync_UB_tree

# Calculate the number of hours, minutes and seconds for t_sync_UB_tree
time_hms = convert_sec_into_hms(t_sync_UB_hybrid)

f.write("    The time to synchronize all Apollo devices on a Unit Board is: ")
f.write(str(round(t_sync_UB_hybrid, 3)))
f.write(" seconds, that is ")
f.write(str(time_hms))
f.write("\n")

# Calculate the synchronization time of all Aion devices on the System Board
t_sync_SB_hybrid = (
    N_Aion_SB_hybrid * (t_Aion_cfg + t_Aion_sync)
    + N_UB_hybrid * N_Aion_UB_hybrid * t_Aion_Apollo_tof
    + t_Aion_FPGA_tof
)

# Calculate the number of hours, minutes and seconds for t_sync_SB
time_hms = convert_sec_into_hms(t_sync_SB_hybrid)

f.write("    The time to synchronize all Aion devices on a System Board is: ")
f.write(str(round(t_sync_SB_hybrid, 3)))
f.write(" seconds, that is ")
f.write(str(time_hms))
f.write("\n")

# Calculate the total synchronization time of the hybrid system
t_sync_all_hybrid = t_sync_SB_hybrid + t_sync_UB_hybrid

# Calculate the number of hours, minutes and seconds for t_sync_all_tree
time_hms = convert_sec_into_hms(t_sync_all_hybrid)

f.write("    The time to synchronize all Apollo devices in the system is: ")
f.write(str(round(t_sync_all_hybrid)))
f.write(" seconds, that is ")
f.write(str(time_hms))
f.write("\n")

# calculate the alignment error sigma distribution between the 1st BSYNC channel
# of the 1st Aion in the cascade and the last BSYNC channel of the last Aion
# of the last Unit Board in the tree
# sigma is sqrt(len(M_tree))*2.36ps
sigma_alignment_hybrid = sqrt(N_Aion_SB_hybrid + 2) * 10 / 3 / sqrt(2)
f.write("    One sigma alignment error between the first BSYNC channel of the ")
f.write(
    "first Aion on the top Unit Board and the \n        last BSYNC channel of the last Aion "
)
f.write("of the bottom Unit Board is: ")
f.write(str(round(sigma_alignment_hybrid, 3)))
f.write(" ps")
f.write("\n")

f.write("    Three sigma alignment error between the first BSYNC channel of the ")
f.write(
    "first Aion on the top Unit Board and the \n        last BSYNC channel of the last Aion "
)
f.write("of the bottom Unit Board is: ")
f.write(str(round(3 * sigma_alignment_hybrid, 3)))
f.write(" ps")
f.write("\n")

###############################################################################
# Calculations for a Hybrid Tree - Cascade Architecture
###############################################################################
f.write("----------------------------------------------------------------------\n")
f.write("This is the proposal for a hybrid tree - cascade architecture\n")
f.write("----------------------------------------------------------------------\n")


# the number of Aion devices on a Unit Board is calculated
N_Aion_UB_hybrid2 = ceil((N_Apollo - 7) / 8) + 1

f.write("     The number of Aion devices per Unit Board is : ")
f.write(str(N_Aion_UB_hybrid2))
f.write("\n")

# The number of Aion devices assigned to every FPGA on the Unit Board is calculated
(N_Aion_per_FPGA_hybrid2, Max_Aion_per_FPGA_hybrid2) = Aion_per_FPGA_cascade(
    N_Aion_UB_hybrid2, N_FPGA
)

for index in range(0, len(N_Aion_per_FPGA_hybrid2)):
    f.write("          FPGA[")
    f.write(str(index))
    f.write("] manages:")
    f.write(str(N_Aion_per_FPGA_hybrid2[index]))
    if N_Aion_per_FPGA_hybrid2[index] == 1:
        f.write(" Aion device")
    else:
        f.write(" Aion devices")
    f.write("\n")

if len(N_Aion_per_FPGA_hybrid2) < N_FPGA:
    if N_FPGA - len(N_Aion_per_FPGA_hybrid2) == 1:
        f.write("          One FPGA device does not manage any Aion")
    else:
        f.write("          ")
        f.write(str(N_FPGA - len(N_Aion_per_FPGA_hybrid2)))
        f.write(" FPGA devices do not manage any Aion")
        f.write("\n")

f.write("    The maximum number of Aion devices per FPGA on the Unit Board is: ")
f.write(str(Max_Aion_per_FPGA_hybrid2))
f.write("\n")

# the number of Apollo devices assigned per Aion is calculated
N_Apollo_per_Aion_hybrid2 = Apollo_per_Aion_cascade(N_Apollo, N_Aion_UB_hybrid2)

# write the results in the output file
f.write("    The number of Apollo devices per Unit Board is: ")
f.write(str(N_Apollo))
f.write("\n")
for index in range(0, ceil((N_Apollo - 7) / 8) + 1):
    f.write("          Aion[")
    f.write(str(index))
    f.write("] manages:")
    f.write(str(N_Apollo_per_Aion_hybrid2[index]))
    f.write(" Apollo devices")
    f.write("\n")

# the maximum number of Apollo devices managed by one FPGA on a Unit Board is
# calculated
Max_Apollo_per_FPGA_hybrid2 = 0
for index in range(0, N_FPGA):
    temp = 0
    for index2 in range(0, N_Aion_per_FPGA_hybrid2[index]):
        temp = temp + N_Apollo_per_Aion_hybrid2[index2]
    Max_Apollo_per_FPGA_hybrid2 = max(Max_Apollo_per_FPGA_hybrid2, temp)

f.write("    The maximum number of Apollo devices per FPGA on the Unit Board is: ")
f.write(str(Max_Apollo_per_FPGA_hybrid2))
f.write("\n")

# the number of Unit Boards N_UB is calculated
N_UB_hybrid2 = math.ceil(N / N_Apollo)

f.write("    The number of Unit Boards in the system is ")
f.write(str(N_UB_hybrid2))
f.write("\n")


# we calculate the number of Unit Boards on a branch N_UB_branch
N_UB_per_branch = []
Allocated_UB = 0
for index in range(0, N_branch):
    number = math.ceil((N_UB_hybrid2 - Allocated_UB) / (N_branch - index))
    N_UB_per_branch.append(number)
    Allocated_UB = Allocated_UB + number

f.write("    The number of Unit Boards assigned per branch is:\n")
for index in range(0, N_branch):
    f.write("        Branch(")
    f.write(str(index))
    f.write(") contains ")
    f.write(str(N_UB_per_branch[index]))
    f.write(" Unit Boards\n")


# the number of Aion devices on the System Board is calculated
index = 0
N_Aion_SB_hybrid2 = 0
M_tree_hybrid2 = []
# the first column of Aion tree consists in the number of branches N_branch
# because only the first Aion on the first Unit Board in the branch cascade is
# connected to the System Board
M_tree_hybrid2.append(N_branch)
while M_tree_hybrid2[index] > 1:
    number = math.ceil(M_tree_hybrid2[index] / 9)
    index += 1
    M_tree_hybrid2.append(number)
    N_Aion_SB_hybrid2 = N_Aion_SB_hybrid2 + M_tree_hybrid2[index]

f.write("    The number of Aion devices on a System Board is: ")
f.write(str(N_Aion_SB_hybrid2))
f.write("\n")


if N_Aion_SB_hybrid2 > 1:
    f.write("    The number of Aion devices per tree column on the System Board is:\n")
    for index in range(1, len(M_tree_hybrid2)):
        if M_tree_hybrid2[index] == 1:
            f.write("        Tree Column number ")
            f.write(str(index))
            f.write(" has ")
            f.write(str(M_tree_hybrid2[index]))
            f.write(" Aion device")
            f.write("\n")
        else:
            f.write("        Tree Column number ")
            f.write(str(index))
            f.write(" has ")
            f.write(str(M_tree_hybrid2[index]))
            f.write(" Aion devices")
            f.write("\n")

# the total number of Aion devices in the system is:
N_Aion_system_hybrid2 = N_UB_hybrid2 * N_Aion_UB_hybrid2 + N_Aion_SB_hybrid2
f.write(
    "    The number of Aion devices in the system (on the System Board and all Unit Boards) is: "
)
f.write(str(N_Aion_system_hybrid2))
f.write("\n")


# the synchronization time of all Apollo devices on a Unit Board in this hybrid
# tree-cascade system is equal to the synchronization time of a Unit Board into
# a cascade system:
t_sync_UB_hybrid2 = (
    t_Apollo_boot
    + Max_Apollo_per_FPGA_hybrid2 * (t_Apollo_cfg + t_MCS_cfg + t_Apollo_sync)
    + Max_Aion_per_FPGA_hybrid2 * (t_Aion_cfg + t_Aion_sync)
    + N_Apollo * t_Aion_Apollo_tof
    + N_FPGA * t_Aion_FPGA_tof
)

# Calculate the number of hours, minutes and seconds for t_sync_UB_tree
time_hms = convert_sec_into_hms(t_sync_UB_hybrid2)

f.write("    The time to synchronize all Apollo devices on a Unit Board is: ")
f.write(str(round(t_sync_UB_hybrid2, 3)))
f.write(" seconds, that is ")
f.write(str(time_hms))
f.write("\n")


# Calculate the synchronization time of all Aion devices on the System Board
t_sync_SB_hybrid2 = (
    N_Aion_SB_hybrid2 * (t_Aion_cfg + t_Aion_sync)
    + (N_Aion_SB_hybrid2 - 1 + M_tree_hybrid2[0]) * t_Aion_Apollo_tof
    + t_Aion_FPGA_tof
)

# Calculate the number of hours, minutes and seconds for t_sync_SB
time_hms = convert_sec_into_hms(t_sync_SB_hybrid2)

f.write("    The time to synchronize all Aion devices on a System Board is: ")
f.write(str(round(t_sync_SB_hybrid2, 3)))
f.write(" seconds, that is ")
f.write(str(time_hms))
f.write("\n")


# Calculate the synchronization time of the Unit Boards placed on a branch
t_sync_branch = (
    t_Apollo_boot
    + Max_Apollo_per_FPGA_hybrid2 * (t_Apollo_cfg + t_MCS_cfg + t_Apollo_sync)
    + Max_Aion_per_FPGA_hybrid2 * (t_Aion_cfg + t_Aion_sync)
    + max(N_UB_per_branch) * (N_Apollo * t_Aion_Apollo_tof + N_FPGA * t_Aion_FPGA_tof)
)

# Calculate the number of hours, minutes and seconds for t_sync_branch
time_hms = convert_sec_into_hms(t_sync_branch)

f.write("    The time to synchronize all Apollo devices on a branch is: ")
f.write(str(t_sync_branch))
f.write(" seconds, that is ")
f.write(str(time_hms))
f.write("\n")

# Calculate the total synchronization time of the hybrid system
t_sync_all_hybrid2 = t_sync_branch + t_sync_SB_hybrid2

# Calculate the number of hours, minutes and seconds for t_sync_all_tree
time_hms = convert_sec_into_hms(t_sync_all_hybrid2)

f.write("    The time to synchronize all Apollo devices in the system is: ")
f.write(str(round(t_sync_all_hybrid2, 3)))
f.write(" seconds, that is ")
f.write(time_hms)
f.write("\n")


# calculate the alignment error sigma distribution between the 1st BSYNC channel
# of the 1st Aion in the tree and the last BSYNC channel of the last Aion
# of the last Unit Board in the branch cascade
# sigma is sqrt(len(M_tree)-1 + N_UB_branch * N_Aion_hybrid2)*2.36ps
sigma_alignment_hybrid2 = (
    sqrt(len(M_tree_hybrid2) - 1 + max(N_UB_per_branch) * N_Aion_UB_hybrid2)
    * 10
    / 3
    / sqrt(2)
)
f.write("    One sigma alignment error between the first BSYNC channel of the ")
f.write("first Aion in the tree and the \n        last BSYNC channel of the last Aion ")
f.write("of the last Unit Board in the branch cascade is: ")
f.write(str(round(sigma_alignment_hybrid2, 3)))
f.write(" ps")
f.write("\n")


f.write("    Three sigma alignment error between the first BSYNC channel of the ")
f.write("first Aion in the tree and the \n        last BSYNC channel of the last Aion ")
f.write("of the last Unit Board in the branch cascade is: ")
f.write(str(round(3 * sigma_alignment_hybrid2, 3)))
f.write(" ps")
f.write("\n")

f.close()

print(f"Results have been written in the file: {root + filen.split('.')[0]}.dat")