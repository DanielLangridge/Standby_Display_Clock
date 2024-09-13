import storage
import microcontroller

nvm = microcontroller.nvm
setupRequest = nvm[:1] # Check the first byte of NVM to see if we should enter setup mode of not
setupRequest = not(setupRequest[0] == 0x01)

print("Boot setupRequest:", setupRequest)

# If the unit will enter SetupMode, disable readonly to enable wireless code updates
storage.remount("/", readonly=setupRequest)