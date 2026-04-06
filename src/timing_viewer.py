"""
타이밍 다이어그램 뷰어 + 파형 생성기
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
포함 클래스:
  - WaveformGenerator : Signal 파라미터 → (time[], voltage[]) 배열 변환
                        [통합] 구 waveform_generator.py에서 이동
  - TimingViewer      : Matplotlib 기반 타이밍 다이어그램 위젯

파형 생성 모드 (WaveformGenerator)
────────────────────────────────────
1. DC 모드 (delay=0, width=0, period=0)
   SIG_MODE/INV 에 따라 프레임별 일정 전압 출력:
     MODE=0, INV=0 → V1 고정
     MODE=0, INV=1 → 프레임별 V1↔V2
     MODE=1, INV=0 → 프레임별 V1↔V3
     MODE=1, INV=1 → 프레임별 V1↔V4

2. 반복 펄스 모드 (period > 0)
   period 주기로 delay→V1, width→V2, 나머지→V1 반복

3. 단일 펄스 모드 (period = 0, width > 0)
   0~delay: V1, delay~delay+width: V2, 이후: V1

TimingViewer 업데이트 이력
───────────────────────────
  V10: 신호 높이 고정, Y축에 신호 이름, 내부에 전압 레이블
  V11: 범례 위치 설정, v1~v4 레이블, Frame/Time(us) 모드
  V12: [통합] WaveformGenerator 인라인
       모델 클릭 시 비동기(after 50ms) 업데이트로 속도 개선
"""

import tkinter as tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import numpy as np


# ════════════════════════════════════════════════════════
# WaveformGenerator — 파형 데이터 생성
# [통합] 구 waveform_generator.py에서 이동
# ════════════════════════════════════════════════════════

class WaveformGenerator:
    """
    Signal 파라미터를 받아 Matplotlib 플롯용 파형 배열을 생성합니다.

    단위:
      - 입력 시간 파라미터 : us (마이크로초)
      - 입력 sync_data   : 초 (second) → 내부에서 us로 변환
      - 출력 time 배열   : us
      - 출력 voltage 배열: V
    """

    @staticmethod
    def generate_waveform(signal, num_frames: int, sync_data: float):
        """
        신호 파형 배열 생성.

        Args:
            signal    : Signal 객체 (v1~v4, delay, width, period, sig_mode, inversion)
            num_frames: 표시할 프레임 수
            sync_data : 1프레임 길이 (초 단위) — 내부에서 us로 변환됨

        Returns:
            tuple(np.ndarray, np.ndarray):
              - time_array    : 시간 축 (us)
              - voltage_array : 전압 축 (V)
        """
        # DC 모드 판별: delay, width, period 모두 0이면 DC 고정 출력
        is_dc = (signal.delay == 0 and signal.width == 0 and signal.period == 0)

        # sync_data(초) → us 변환 (파라미터와 단위 일치)
        frame_us    = sync_data * 1_000_000
        total_us    = frame_us * num_frames

        # 시간 배열: 프레임당 2000 포인트로 충분한 해상도 확보
        n_pts   = 2000 * num_frames
        time    = np.linspace(0, total_us, n_pts)
        voltage = np.zeros_like(time)

        for f_idx in range(num_frames):
            f_start  = f_idx * frame_us
            f_end    = (f_idx + 1) * frame_us
            mask     = (time >= f_start) & (time < f_end)
            rel_time = time[mask] - f_start       # 프레임 내 상대 시간 (us)

            # 프레임 번호(1-based), 홀수/짝수 판별
            is_odd = ((f_idx + 1) % 2) == 1

            if is_dc:
                # ── DC 모드 ───────────────────────────────
                # SIG_MODE·INV에 따라 프레임별 고정 전압 결정
                v = WaveformGenerator._dc_voltage(signal, is_odd)
                voltage[mask] = v
            else:
                # ── 펄스 모드 ─────────────────────────────
                # SIG_MODE·INV에 따라 (low, high) 전압 쌍 결정
                low_v, high_v = WaveformGenerator._pulse_levels(signal, is_odd)
                frame_v = np.full(rel_time.shape, low_v)  # 기본: low 전압

                if signal.period > 0:
                    # 반복 펄스: period 주기로 패턴 반복
                    # phase가 [delay, delay+width) 구간이면 high 전압
                    phase = rel_time % signal.period
                    hi_mask = (phase >= signal.delay) & (
                        phase < signal.delay + signal.width)
                else:
                    # 단일 펄스: 프레임 내 [delay, delay+width) 구간만 high
                    hi_mask = (rel_time >= signal.delay) & (
                        rel_time < signal.delay + signal.width)

                frame_v[hi_mask] = high_v
                voltage[mask] = frame_v

        return time, voltage

    @staticmethod
    def _dc_voltage(signal, is_odd: bool) -> float:
        """
        DC 모드에서 현재 프레임의 전압값 결정.

        SIG_MODE / INVERSION 조합:
          MODE=0, INV=0 → 항상 V1
          MODE=0, INV=1 → 홀수 V1, 짝수 V2
          MODE=1, INV=0 → 홀수 V1, 짝수 V3
          MODE=1, INV=1 → 홀수 V1, 짝수 V4

        Args:
            signal : Signal 객체
            is_odd : 현재 프레임이 홀수이면 True

        Returns:
            float: 결정된 DC 전압 (V)
        """
        if signal.sig_mode == 0:
            if signal.inversion == 0:
                return signal.v1                              # 고정 V1
            return signal.v1 if is_odd else signal.v2        # V1↔V2 교대
        else:  # sig_mode == 1
            if signal.inversion == 0:
                return signal.v1 if is_odd else signal.v3    # V1↔V3 교대
            return signal.v1 if is_odd else signal.v4        # V1↔V4 교대

    @staticmethod
    def _pulse_levels(signal, is_odd: bool):
        """
        펄스 모드에서 (low_voltage, high_voltage) 쌍 결정.

        SIG_MODE / INVERSION 조합:
          MODE=0, INV=0 → 모든 프레임 (V1, V2)
          MODE=0, INV=1 → 홀수 (V1,V2), 짝수 (V2,V1) — High↔Low 교대
          MODE=1, INV=0 → 홀수 (V1,V2), 짝수 (V3,V4)
          MODE=1, INV=1 → 홀수 (V1,V2), 짝수 (V4,V3)

        Args:
            signal : Signal 객체
            is_odd : 현재 프레임이 홀수이면 True

        Returns:
            tuple(float, float): (low_voltage, high_voltage)
        """
        if signal.sig_mode == 0:
            if signal.inversion == 0:
                return signal.v1, signal.v2              # 항상 V1/V2
            # 짝수 프레임은 V1·V2 순서 반전
            return (signal.v1, signal.v2) if is_odd else (signal.v2, signal.v1)
        else:  # sig_mode == 1
            if is_odd:
                return signal.v1, signal.v2              # 홀수: V1/V2
            # 짝수: V3/V4 또는 V4/V3 (inversion에 따라)
            if signal.inversion == 0:
                return signal.v3, signal.v4
            return signal.v4, signal.v3

    @staticmethod
    def get_voltage_range(signals):
        """
        신호 리스트에서 전체 전압 범위(min, max) 계산.

        타이밍 다이어그램 Y축 범위 설정에 사용됩니다.

        Args:
            signals: Signal 객체 리스트

        Returns:
            tuple(float, float): (min_voltage, max_voltage)
        """
        if not signals:
            return 0.0, 5.0
        all_v = [v for s in signals for v in (s.v1, s.v2, s.v3, s.v4)]
        return min(all_v), max(all_v)


class TimingViewer(tk.Frame):
    """
    타이밍 다이어그램 뷰어 위젯
    
    여러 신호의 파형을 시각화합니다.
    - 개별 보기(Separate): 신호를 수직으로 분리하여 표시
    - 합쳐 보기(Combined): 모든 신호를 하나의 축에 중첩하여 표시
    
    V10 업데이트:
    - 신호 높이 조절 제거 (기본 스케일 사용)
    - Y축 레이블: 신호 이름은 축에, 전압 값은 그래프 내부에 표시
    - 호버 정보: 마우스 X 위치의 실제 신호 전압값 표시
    
    V11 업데이트:
    - 범례 위치 변경 기능 추가
    - 전압 레이블을 v1, v2, v3, v4로 표시
    - Line 단위 제거 (Frame/Time(us)만 사용)
    """
    
    def __init__(self, parent, signal_manager, sync_data_manager):
        """
        초기화 메서드
        
        Args:
            parent: 부모 위젯
            signal_manager (SignalManager): 신호 관리자
            sync_data_manager (SyncDataManager): SyncData 관리자
        """
        super().__init__(parent)
        
        self.signal_manager = signal_manager
        self.sync_data_manager = sync_data_manager
        self.num_frames = 2  # 기본 표시 프레임 수
        self.show_grid = True  # 그리드 표시 여부
        self.view_mode = "separate"  # "separate" or "combined"
        self.view_time = None  # X축 제한 시간 (us), None이면 전체 표시
        self.x_axis_mode = "frame"  # "frame" or "time"
        self.legend_location = "upper right"  # 범례 위치
        
        # 호버 시 전압 계산을 위한 데이터 저장소
        self.plot_data = {} # {signal_name: {'time': [], 'voltage': [], 'offset': 0}}
        self.signal_bands = [] # (y_min, y_max, signal_name) - 호버 감지용
        
        self._setup_ui()
        
        # 신호 변경 시 그래프 자동 업데이트를 위한 리스너 등록
        self.signal_manager.add_listener(self.update_plot)
    
    def _setup_ui(self):
        """UI 구성"""
        # Matplotlib Figure 생성 (좌측 여백 확보를 위해 subplot 조정)
        self.figure = Figure(figsize=(12, 6), dpi=100)
        self.figure.subplots_adjust(left=0.15) # Y축 레이블 공간 확보
        self.ax = self.figure.add_subplot(111)
        
        # Tkinter 캔버스에 Figure 연결
        self.canvas = FigureCanvasTkAgg(self.figure, self)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # 네비게이션 툴바 추가 (줌, 팬 기능)
        toolbar = NavigationToolbar2Tk(self.canvas, self)
        toolbar.update()
        
        # 마우스 이벤트 연결 (호버 기능)
        self.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)
        
        # Crosshair 라인 생성 (초기에는 숨김)
        self.vline = None
        self.text = None
        
        # 초기 그래프 그리기
        self.update_plot()
    
    def set_num_frames(self, num_frames):
        """표시할 프레임 수 설정"""
        self.num_frames = max(1, num_frames)
        self.update_plot()
    
    def toggle_grid(self):
        """그리드 표시/숨김 토글"""
        self.show_grid = not self.show_grid
        self.update_plot()
        
    def set_view_mode(self, mode):
        """뷰 모드 설정 (separate/combined)"""
        self.view_mode = mode
        self.update_plot()
        
    def set_legend_location(self, location):
        """범례 위치 설정
        
        Args:
            location (str): 범례 위치 ('upper right', 'upper left', 'lower right', 'lower left')
        """
        self.legend_location = location
        self.update_plot()
        
    def set_view_time(self, time_us):
        """뷰 시간 설정 (X축 제한, us 단위)"""
        self.view_time = time_us
        self.update_plot()
    
    def set_x_axis_mode(self, mode):
        """X축 모드 설정 (frame/time)"""
        self.x_axis_mode = mode
        self.update_plot()
    
    def update_plot(self):
        """타이밍 다이어그램 업데이트"""
        self.ax.clear()
        self.plot_data = {} # 데이터 초기화
        
        # Crosshair 초기화
        self.vline = self.ax.axvline(x=0, color='gray', linestyle='--', linewidth=0.8, alpha=0)
        self.text = self.ax.text(0, 0, '', color='black', fontsize=9, 
                                bbox=dict(facecolor='white', alpha=0.9, edgecolor='gray'))
        self.text.set_visible(False)
        
        signals = self.signal_manager.get_all_signals()
        
        # V11: visible=True인 신호만 필터링
        visible_signals = [s for s in signals if getattr(s, 'visible', True)]
        
        if not visible_signals:
            self.ax.text(0.5, 0.5, 'No visible signals to display', 
                        ha='center', va='center', fontsize=14,
                        transform=self.ax.transAxes, color='black')
            self.canvas.draw()
            return
        
        sync_data = self.sync_data_manager.get_current_sync_data()
        
        # 신호 영역 정보 초기화 (호버 감지용)
        self.signal_bands = [] # (y_min, y_max, signal_name)
        
        if self.view_mode == "separate":
            self._plot_separate(visible_signals, sync_data, WaveformGenerator)
        else:
            self._plot_combined(visible_signals, sync_data, WaveformGenerator)
            
        # 공통 설정
        self._draw_frame_dividers(sync_data, len(visible_signals))
        
        # 축 레이블 및 타이틀
        self.ax.set_xlabel('Time (us)', fontsize=11, color='black')
            
        self.ax.set_title(f'Timing Diagram - {self.sync_data_manager.current_model} @ {self.sync_data_manager.current_frequency}Hz',
                         fontsize=12, fontweight='bold', color='black')
        
        # X축 범위 설정 (X-axis Mode 및 View Time 적용)
        if self.x_axis_mode == "time":
            # 시간 모드: view_time 사용
            if self.view_time and self.view_time > 0:
                self.ax.set_xlim(0, self.view_time)
            else:
                # view_time이 없으면 2 프레임 분량 표시
                self.ax.set_xlim(0, sync_data * 1000000 * 2)
        else:
            # 프레임 모드: num_frames 사용
            self.ax.set_xlim(0, sync_data * 1000000 * self.num_frames)
        
        # 그리드 설정
        if self.show_grid:
            self.ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        
        # tight_layout 대신 subplots_adjust만 사용 (경고 방지)
        self.figure.subplots_adjust(left=0.15, right=0.95, top=0.93, bottom=0.1)
        
        self.canvas.draw()
        
    def _plot_separate(self, signals, sync_data, generator):
        """개별 보기 모드 그리기"""
        
        current_y_cursor = 0.0
        margin = 2.0
        
        # Y축 틱과 라벨을 위한 리스트
        yticks = []
        yticklabels = []
        
        # 마지막 신호가 가장 아래에 오도록 역순 순회
        for idx in range(len(signals) - 1, -1, -1):
            signal = signals[idx]
            time, voltage = generator.generate_waveform(signal, self.num_frames, sync_data)
            
            # 전압 범위 계산
            v_min = min(signal.v1, signal.v2, signal.v3, signal.v4)
            v_max = max(signal.v1, signal.v2, signal.v3, signal.v4)
            
            # 신호의 실제 높이
            signal_height = v_max - v_min
            if signal_height < 1.0: signal_height = 1.0
            
            # 배치할 오프셋 계산 (v_min이 current_y_cursor에 오도록)
            offset = current_y_cursor - v_min
            
            # 데이터 저장 (호버용)
            self.plot_data[signal.name] = {
                'time': time,
                'voltage': voltage, # 실제 전압값 저장
                'offset': offset,   # 그래프상 오프셋
                'y_min': current_y_cursor,
                'y_max': current_y_cursor + signal_height
            }
            
            # 신호 색상
            color = getattr(signal, 'color', 'blue')
            if not color: color = 'blue'
            
            # 파형 그리기 (구형파: steps-post)
            self.ax.plot(time, voltage + offset, color=color,
                         linewidth=1.5, label=signal.name,
                         drawstyle='steps-post')
            
            # 신호 영역 배경 (구분감)
            bg_bottom = current_y_cursor - (margin / 4)
            bg_top = current_y_cursor + signal_height + (margin / 4)
            
            if idx % 2 == 0:
                self.ax.axhspan(bg_bottom, bg_top, color='#f0f0f0', alpha=0.5, zorder=0)
            
            # 호버 감지를 위해 영역 저장
            self.signal_bands.append((bg_bottom, bg_top, signal.name))
            
            # Y축 레이블 설정 (그래프 외부 좌측 - 신호 이름만)
            mid_y = current_y_cursor + signal_height / 2
            yticks.append(mid_y)
            yticklabels.append(signal.name)
            
            # 전압 값 표시 (그래프 내부) - v1, v2, v3, v4로 표시
            # 시작점에 전압 레벨 표시
            self.ax.text(time[0], current_y_cursor, f"Low: {v_min:.1f}V", 
                        ha='left', va='bottom', fontsize=8, color='gray', alpha=0.8)
            self.ax.text(time[0], current_y_cursor + (v_max - v_min), f"High: {v_max:.1f}V", 
                        ha='left', va='bottom', fontsize=8, color='gray', alpha=0.8)
            
            # 다음 신호를 위해 커서 이동
            current_y_cursor += signal_height + margin
            
        # Y축 틱 설정
        self.ax.set_yticks(yticks)
        self.ax.set_yticklabels(yticklabels, fontsize=9, fontweight='bold')
        self.ax.tick_params(axis='y', pad=5)
        
        # Y축 범위 설정
        self.ax.set_ylim(-margin, current_y_cursor)

    def _plot_combined(self, signals, sync_data, generator):
        """합쳐 보기 모드 그리기"""
        all_v_min = float('inf')
        all_v_max = float('-inf')
        
        for signal in signals:
            time, voltage = generator.generate_waveform(signal, self.num_frames, sync_data)
            
            # 데이터 저장 (호버용)
            self.plot_data[signal.name] = {
                'time': time,
                'voltage': voltage,
                'offset': 0
            }
            
            # 신호 색상 가져오기
            color = getattr(signal, 'color', None)
            
            self.ax.plot(time, voltage, linewidth=1.5, label=signal.name, color=color,
                         drawstyle='steps-post')

            
            # 전체 전압 범위 갱신
            v_min = min(signal.v1, signal.v2, signal.v3, signal.v4)
            v_max = max(signal.v1, signal.v2, signal.v3, signal.v4)
            all_v_min = min(all_v_min, v_min)
            all_v_max = max(all_v_max, v_max)
            
        # 범례 표시 (위치 설정 가능)
        self.ax.legend(loc=self.legend_location, fontsize=9)
        
        # Y축 오토스케일링 (여백 추가)
        if all_v_min == float('inf'): # 신호가 없는 경우 등
            all_v_min, all_v_max = 0, 5
            
        margin = (all_v_max - all_v_min) * 0.1 if all_v_max != all_v_min else 1.0
        self.ax.set_ylim(all_v_min - margin, all_v_max + margin)
        self.ax.set_ylabel('Voltage (V)', fontsize=11, color='black')

    def _draw_frame_dividers(self, sync_data, num_signals):
        """프레임 구분선 그리기"""
        frame_length_us = sync_data * 1000000 # us
        frame_length = frame_length_us
        
        # Y축 범위 가져오기 (구분선 높이 설정용)
        ylim = self.ax.get_ylim()
        
        for frame_idx in range(1, self.num_frames + 1):
            x_pos = frame_idx * frame_length
            self.ax.axvline(x=x_pos, color='red', linestyle=':', linewidth=1, alpha=0.5)
            
            # 프레임 번호 표시 (상단)
            self.ax.text(x_pos - frame_length/2, ylim[1], 
                        f'Frame {frame_idx}',
                        ha='center', va='bottom', fontsize=9, color='red')

    def _on_mouse_move(self, event):
        """마우스 이동 이벤트 핸들러 (Crosshair 및 실제 전압 값 표시)"""
        if not event.inaxes:
            if self.vline: self.vline.set_alpha(0)
            if self.text: self.text.set_visible(False)
            self.canvas.draw_idle()
            return
        
        x, y = event.xdata, event.ydata
        
        # Crosshair 위치 업데이트 (수직선만 표시)
        self.vline.set_xdata([x])
        self.vline.set_alpha(0.8)
        
        # 텍스트 정보 구성
        info_text = f"Time: {x:.1f} us\n"
        
        # 해당 X 위치에서의 각 신호 전압값 찾기
        found_signal = False
        
        if self.view_mode == "separate":
            # 마우스가 위치한 밴드의 신호 찾기
            target_signal = None
            if self.signal_bands:  # signal_bands가 비어있지 않은 경우에만
                for y_min, y_max, name in self.signal_bands:
                    if y_min <= y <= y_max:
                        target_signal = name
                        break
            
            if target_signal and target_signal in self.plot_data:
                data = self.plot_data[target_signal]
                # X값에 가장 가까운 인덱스 찾기
                idx = (np.abs(data['time'] - x)).argmin()
                voltage = data['voltage'][idx]
                info_text += f"[{target_signal}]: {voltage:.2f} V"
                found_signal = True
            else:
                # 밴드 밖이면 가장 가까운 신호라도 표시? 아니면 표시 안함
                info_text += "No Signal"
                
        else: # Combined mode
            # 모든 신호의 전압 표시 (너무 많으면 복잡할 수 있음, 일단 상위 5개?)
            count = 0
            for name, data in self.plot_data.items():
                idx = (np.abs(data['time'] - x)).argmin()
                voltage = data['voltage'][idx]
                info_text += f"{name}: {voltage:.2f} V\n"
                count += 1
                if count >= 5: # 최대 5개까지만 표시
                    info_text += "..."
                    break
            found_signal = True
        
        # 텍스트 위치 및 표시
        self.text.set_text(info_text)
        
        # 텍스트 박스가 그래프 밖으로 나가지 않도록 조정
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        
        text_x = x + (xlim[1] - xlim[0]) * 0.02
        text_y = y
        
        # 오른쪽 끝이면 왼쪽으로 이동
        if x > xlim[1] * 0.8:
            text_x = x - (xlim[1] - xlim[0]) * 0.15
            
        self.text.set_position((text_x, text_y))
        self.text.set_visible(True)
        
        self.canvas.draw_idle()
