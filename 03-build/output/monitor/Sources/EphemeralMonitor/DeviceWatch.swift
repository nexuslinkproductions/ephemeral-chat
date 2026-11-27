import Foundation
import CoreMediaIO

/// Camera and microphone activation from CoreMediaIO. This reads the public
/// device property `DeviceIsRunningSomewhere`; it never opens a stream, so it
/// needs no camera or microphone permission and cannot record anything.
public enum DeviceWatch {
    public static func cameraOrMicActive() -> Bool {
        var address = CMIOObjectPropertyAddress(
            mSelector: CMIOObjectPropertySelector(kCMIOHardwarePropertyDevices),
            mScope: CMIOObjectPropertyScope(kCMIOObjectPropertyScopeGlobal),
            mElement: CMIOObjectPropertyElement(kCMIOObjectPropertyElementMain)
        )
        var size: UInt32 = 0
        guard CMIOObjectGetPropertyDataSize(CMIOObjectID(kCMIOObjectSystemObject), &address, 0, nil, &size) == noErr else {
            return false
        }
        let count = Int(size) / MemoryLayout<CMIOObjectID>.size
        guard count > 0 else { return false }
        var devices = [CMIOObjectID](repeating: 0, count: count)
        var used: UInt32 = 0
        guard CMIOObjectGetPropertyData(CMIOObjectID(kCMIOObjectSystemObject), &address, 0, nil, size, &used, &devices) == noErr else {
            return false
        }
        for device in devices {
            var running = CMIOObjectPropertyAddress(
                mSelector: CMIOObjectPropertySelector(kCMIODevicePropertyDeviceIsRunningSomewhere),
                mScope: CMIOObjectPropertyScope(kCMIOObjectPropertyScopeGlobal),
                mElement: CMIOObjectPropertyElement(kCMIOObjectPropertyElementMain)
            )
            var value: UInt32 = 0
            var valueSize: UInt32 = 0
            var valueUsed: UInt32 = 0
            if CMIOObjectGetPropertyDataSize(device, &running, 0, nil, &valueSize) == noErr,
               valueSize == UInt32(MemoryLayout<UInt32>.size),
               CMIOObjectGetPropertyData(device, &running, 0, nil, valueSize, &valueUsed, &value) == noErr,
               value != 0 {
                return true
            }
        }
        return false
    }
}
