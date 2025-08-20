# pfr.py  -- MLX90640 logging+MP4 + Enter로 서보 2500/1400µs 토글
import argparse, os, time, signal, sys, datetime as dt, threading
import numpy as np
import cv2
import pigpio

import board, busio
import adafruit_mlx90640 as mlxlib
try:
    import adafruit_tca9548a
    HAS_MUX = True
except Exception:
    HAS_MUX = False

H, W = 24, 32
REG_ADDR = 0x33

def ensure_pigpio():
    pi = pigpio.pi()
    if not pi.connected:
        os.system("sudo pigpiod >/dev/null 2>&1")
        time.sleep(0.3)
        pi = pigpio.pi()
    if not pi.connected:
        raise RuntimeError("pigpio 데몬 연결 실패. 'sudo systemctl enable --now pigpiod' 확인.")
    return pi

def make_i2c(baud=1_000_000):
    # 실제 속도는 /boot/firmware/config.txt에서 설정됨
    return busio.I2C(board.SCL, board.SDA, frequency=baud)

def open_mlx(i2c, addr, rate_hz):
    cam = mlxlib.MLX90640(i2c, address=addr)
    table = {
        0.5: mlxlib.RefreshRate.REFRESH_0_5_HZ,
        1:   mlxlib.RefreshRate.REFRESH_1_HZ,
        2:   mlxlib.RefreshRate.REFRESH_2_HZ,
        4:   mlxlib.RefreshRate.REFRESH_4_HZ,
        8:   mlxlib.RefreshRate.REFRESH_8_HZ,
        16:  mlxlib.RefreshRate.REFRESH_16_HZ,
        32:  mlxlib.RefreshRate.REFRESH_32_HZ,
        64:  mlxlib.RefreshRate.REFRESH_64_HZ,
    }
    chosen = min([k for k in table.keys() if rate_hz <= k], key=lambda x: x)
    cam.refresh_rate = table[chosen]
    return cam

def percentile_scale(samples, p_lo=5, p_hi=95):
    vmin = float(np.percentile(samples, p_lo))
    vmax = float(np.percentile(samples, p_hi))
    if vmax - vmin < 1e-3: vmax = vmin + 1.0
    return vmin, vmax

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--addr", type=lambda x:int(x,0), default=REG_ADDR)
    ap.add_argument("--rate", type=float, default=8.0)
    ap.add_argument("--outdir", type=str, default="sensorlogs/thermal")
    ap.add_argument("--chunk", type=int, default=600)
    ap.add_argument("--video-out", type=str, default="thermal.mp4")
    ap.add_argument("--width", type=int, default=320)
    ap.add_argument("--vmin", type=float, default=None)
    ap.add_argument("--vmax", type=float, default=None)
    ap.add_argument("--mux-addr", type=lambda x:int(x,0), default=None)
    ap.add_argument("--mux-chan", type=int, default=None)
    # 서보 옵션
    ap.add_argument("--servo-pin", type=int, default=18)
    ap.add_argument("--pulse-a", type=int, default=2500)
    ap.add_argument("--pulse-b", type=int, default=1400)
    ap.add_argument("--no-servo", action="store_true", help="서보 사용 안함")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # I2C
    i2c = make_i2c()
    if args.mux_addr is not None and args.mux_chan is not None:
        if not HAS_MUX:
            print("pip install adafruit-circuitpython-tca9548a 필요", file=sys.stderr); sys.exit(1)
        mux = adafruit_tca9548a.TCA9548A(i2c, address=args.mux_addr)
        i2c = mux[args.mux_chan]
    cam = open_mlx(i2c, args.addr, args.rate)

    # 스케일 프리셋/오토
    buf = np.zeros((H*W,), dtype=np.float32)
    if args.vmin is None or args.vmax is None:
        scratch = []
        for _ in range(20):
            cam.getFrame(buf)
            scratch.append(buf.copy())
            time.sleep(0.001)
        scratch = np.concatenate(scratch)
        vmin, vmax = percentile_scale(scratch, 5, 95)
    else:
        vmin, vmax = args.vmin, args.vmax
    print(f"[Scale] vmin={vmin:.2f}°C, vmax={vmax:.2f}°C")

    # 비디오
    vw = None
    if args.video_out:
        height = int(args.width * H / W)
        vw = cv2.VideoWriter(args.video_out, cv2.VideoWriter_fourcc(*"mp4v"), args.rate, (args.width, height))

    # NPZ 버퍼
    chunk_frames = np.zeros((args.chunk, H, W), dtype=np.float32)
    chunk_ts = np.zeros((args.chunk,), dtype=np.float64)
    idx = 0; parts = 0

    # 서보
    pi = None
    current_pw = None
    if not args.no_servo:
        pi = ensure_pigpio()
        current_pw = args.pulse_a
        pi.set_servo_pulsewidth(args.servo_pin, current_pw)

        stop_ev = threading.Event()
        def enter_listener():
            nonlocal current_pw
            try:
                while not stop_ev.is_set():
                    _ = sys.stdin.readline()  # 엔터 대기
                    if stop_ev.is_set(): break
                    current_pw = args.pulse_b if current_pw == args.pulse_a else args.pulse_a
                    pi.set_servo_pulsewidth(args.servo_pin, current_pw)
                    print(f"[SERVO] pulse -> {current_pw} µs", flush=True)
            except Exception as e:
                print("[SERVO] listener err:", e)
        th = threading.Thread(target=enter_listener, daemon=True)
        th.start()
    else:
        stop_ev = None

    # 종료 핸들러
    stop = False
    def handler(sig, frm):
        nonlocal stop
        stop = True
    signal.signal(signal.SIGINT, handler)

    # 루프
    try:
        while not stop:
            try:
                cam.getFrame(buf)
            except Exception as e:
                print("getFrame 실패:", e)
                time.sleep(0.01)
                continue

            now = time.time()
            frame = buf.reshape(H, W)
            chunk_frames[idx] = frame
            chunk_ts[idx] = now
            idx += 1

            # 비디오 프레임
            if vw is not None:
                norm = np.clip((frame - vmin) / (vmax - vmin), 0, 1)
                gray = (norm * 255).astype(np.uint8)
                img = cv2.resize(gray, (args.width, int(args.width * H / W)), interpolation=cv2.INTER_NEAREST)
                img = cv2.applyColorMap(img, cv2.COLORMAP_INFERNO)
                stamp = dt.datetime.fromtimestamp(now).strftime("%H:%M:%S.%f")[:-3]
                cv2.putText(img, f"{stamp}  min:{frame.min():.1f}C max:{frame.max():.1f}C",
                            (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1, cv2.LINE_AA)
                if current_pw is not None:
                    cv2.putText(img, f"SERVO:{current_pw}us", (6, 38),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1, cv2.LINE_AA)
                vw.write(img)

            # 청크 저장
            if idx >= args.chunk:
                ts0 = dt.datetime.fromtimestamp(chunk_ts[0]).strftime("%Y%m%d_%H%M%S")
                fn = os.path.join(args.outdir, f"mlx90640_{ts0}_part{parts:03d}.npz")
                np.savez_compressed(fn, frames=chunk_frames, timestamps=chunk_ts,
                                    shape=(H,W), addr=args.addr, rate=args.rate, vmin=vmin, vmax=vmax)
                print(f"[SAVE] {fn}  ({idx} frames)")
                idx = 0; parts += 1

    finally:
        # 남은 프레임 저장
        if idx > 0:
            ts0 = dt.datetime.fromtimestamp(chunk_ts[0]).strftime("%Y%m%d_%H%M%S")
            fn = os.path.join(args.outdir, f"mlx90640_{ts0}_part{parts:03d}.npz")
            np.savez_compressed(fn, frames=chunk_frames[:idx], timestamps=chunk_ts[:idx],
                                shape=(H,W), addr=args.addr, rate=args.rate, vmin=vmin, vmax=vmax)
            print(f"[SAVE] {fn}  ({idx} frames)")
        if vw is not None:
            vw.release()
        if not args.no_servo and pi is not None:
            if stop_ev: stop_ev.set()
            pi.set_servo_pulsewidth(args.servo_pin, 0)  # off
            pi.stop()
        print("완료.")
if __name__ == "__main__":
    main()
