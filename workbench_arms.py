"""Public workbench IDs and the device channels they address."""

ARM_CHANNELS = {'left': 'can1', 'right': 'can0'}
ARM_BY_CHANNEL = {channel: arm for arm, channel in ARM_CHANNELS.items()}

# Historical profiles and review logs are indexed by their original arm IDs.
PROFILE_WORKBENCH_ARM = {'left': ARM_BY_CHANNEL['can0'], 'right': ARM_BY_CHANNEL['can1']}
WORKBENCH_PROFILE_ARM = {arm: profile for profile, arm in PROFILE_WORKBENCH_ARM.items()}
