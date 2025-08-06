# define arguments of each app (identifier, message ID, ...)
from lib import types

# ────────────────────────── 시스템 공통 ──────────────────────────
class MainAppArg:
    AppID: types.AppID = 1
    AppName = "Main"
    MID_TerminateProcess: types.MID = 100
    MID_SendHK:           types.MID = 101

class HkAppArg:
    AppID: types.AppID = 2
    AppName = "HK"
    MID_ReceiveHK:       types.MID = 201
    MID_SendCombinedHK:  types.MID = 202

class TelemetryAppArg:
    AppID: types.AppID = 3
    AppName = "Telemetry"
    MID_ReceiveTlmData:  types.MID = 301

# ────────────────────────── 센서·서브시스템 ──────────────────────────
class BarometerAppArg:
    AppID: types.AppID = 10
    AppName = "Barometer"
    MID_SendHK:                     types.MID = 1001
    MID_SendBarometerTlmData:       types.MID = 1002
    MID_SendBarometerFlightLogicData: types.MID = 1003
    MID_ResetBarometerMaxAlt:       types.MID = 1004

class GpsAppArg:
    AppID: types.AppID = 12
    AppName = "GPS"
    MID_SendHK:     types.MID = 1201
    MID_SendGpsTlmData: types.MID = 1202
    MID_SendGpsFlightLogicData: types.MID = 1203

class ImuAppArg:
    AppID: types.AppID = 13
    AppName = "IMU"
    MID_SendHK:        types.MID = 1301
    MID_SendImuTlmData: types.MID = 1302
    MID_SendYawData:   types.MID = 1303
    MID_SendImuFlightLogicData: types.MID = 1304


class FlightlogicAppArg:
    AppID: types.AppID = 14
    AppName = "FlightLogic"
    MID_SendHK:                   types.MID = 1401
    MID_PayloadReleaseMotorActivate: types.MID = 1403
    MID_SendCurrentStateToTlm:    types.MID = 1404
    MID_PayloadReleaseMotorStandby: types.MID = 1405
    MID_SendSimulationStatustoTlm: types.MID = 1407
    MID_SendCameraActivateToCam:  types.MID = 1408
    MID_RocketMotorActivate:      types.MID = 1409
    MID_RocketMotorStandby:       types.MID = 1410
    MID_SendMotorStatus:          types.MID = 1411  # 모터 상태를 Comm 앱으로 전송

    # <NEW/> Motor 각도 지시 (Flightlogic → MotorApp)
    MID_SetServoAngle: types.MID = 1402

class CommAppArg:
    AppID: types.AppID = 16
    AppName = "Communication"
    MID_SendHK:        types.MID = 1601
    MID_RouteCmd_CX:   types.MID = 1602
    MID_RouteCmd_ST:   types.MID = 1603
    MID_RouteCmd_SIM:  types.MID = 1604
    MID_RouteCmd_SIMP: types.MID = 1605
    MID_RouteCmd_CAL:  types.MID = 1606   # 공통 CAL 명령
    MID_RouteCmd_MEC:  types.MID = 1607
    MID_RouteCmd_SS:   types.MID = 1608
    MID_RouteCmd_CAM:  types.MID = 1609

class MotorAppArg:
    AppID: types.AppID = 17      # 24에서 17로 변경 (10번대, 중복되지 않게)
    AppName = "Motor"
    MID_SendHK:          types.MID = 1701   # 1 Hz HK (2401에서 1701로 수정)
    # Flightlogic → MotorApp 각도 지시를 Motor 쪽에서 받을 때 사용할 MID
    MID_SetServoAngle:   types.MID = 1702

# ────────── FIR1 (MLX90614 Channel 0) ──────────
class FirApp1Arg:
    AppID: types.AppID = 20          # **고유해야 함**
    AppName = "FIR1"
    MID_SendHK:            types.MID = 2001
    MID_SendFIR1Data:      types.MID = 2002  # 1 Hz 텔레메트리 (amb,obj)
    MID_Fir1Calibration:   types.MID = 2004  # CAL 처리용(옵션)

# ────────── THERMIS (ADS1115) ──────────
class ThermisAppArg:
    AppID: types.AppID = 24          # **고유해야 함**
    AppName = "THERMIS"
    MID_SendHK:            types.MID = 2401
    MID_SendThermisTlmData:    types.MID = 2402  # 1 Hz 텔레메트리 (temp)
    MID_SendThermisFlightLogicData: types.MID = 2403  # 10 Hz 온도
    MID_ThermisCalibration:    types.MID = 2404  # CAL 처리용(옵션)

# ────────── PITOT (Differential Pressure) ──────────
class PitotAppArg:
    AppID: types.AppID = 25          # **고유해야 함**
    AppName = "PITOT"
    MID_SendHK:            types.MID = 2501
    MID_SendPitotTlmData:    types.MID = 2502  # 1 Hz 텔레메트리 (pressure, temp)
    MID_SendPitotFlightLogicData: types.MID = 2503  # 5 Hz 차압, 온도
    MID_PitotCalibration:    types.MID = 2504  # CAL 처리용(옵션)




class ThermalcameraAppArg:
    AppID: types.AppID = 22          # ← 20과 중복되던 부분 수정
    AppName = "ThermalCamera"
    MID_SendHK: types.MID = 2201
    MID_SendCamTlmData: types.MID = 2202
    MID_SendCamFlightLogicData: types.MID = 2203


class ThermoAppArg:
    AppID: types.AppID = 23
    AppName = "Thermo"           # DHT11 모듈
    MID_SendHK:                       types.MID = 2301

    # <NEW/> 10 Hz: Flightlogic 용 데이터  "temp,humidity"
    MID_SendThermoFlightLogicData:    types.MID = 2302
    # 선택: 1 Hz 텔레메트리
    MID_SendThermoTlmData:            types.MID = 2303

# ────────── TMP007 (Temperature Sensor) ──────────
class Tmp007AppArg:
    AppID: types.AppID = 26          # **고유해야 함**
    AppName = "TMP007"
    MID_SendHK:            types.MID = 2601
    MID_SendTmp007TlmData:    types.MID = 2602  # 1 Hz 텔레메트리 (object_temp, die_temp, voltage)
    MID_SendTmp007FlightLogicData: types.MID = 2603  # 4 Hz 온도 데이터
    MID_Tmp007Calibration:    types.MID = 2604  # CAL 처리용(옵션)

# ────────── CAMERA (Raspberry Pi Camera Module v3 Wide) ──────────
class CameraAppArg:
    AppID: types.AppID = 27          # **고유해야 함**
    AppName = "Camera"
    MID_SendHK:            types.MID = 2701
    MID_SendCameraTlmData:    types.MID = 2702  # 1 Hz 텔레메트리 (status, file_count)
    MID_SendCameraFlightLogicData: types.MID = 2703  # 5 Hz 카메라 상태
    MID_CameraActivate:    types.MID = 2704  # FlightLogic에서 카메라 활성화 명령
    MID_CameraDeactivate:  types.MID = 2705  # FlightLogic에서 카메라 비활성화 명령


# ────────── 샘플/테스트 앱 ──────────
class SampleAppArg:
    AppID: types.AppID = 99
    AppName = "Sample"
    MID_SendHK: types.MID = 9901
