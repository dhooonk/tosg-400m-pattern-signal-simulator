"""
파형 생성 모듈
신호 파라미터를 기반으로 타이밍 파형 데이터를 생성합니다.

=== 파형 생성 로직 요약 ===

1. DC 모드 (Delay=0, Width=0, Period=0):
   - 프레임 전체에 걸쳐 일정한 DC 전압 출력
   - SIG MODE와 INVERSION에 따라 프레임별 전압 결정

2. 일반 모드 (Delay, Width, Period 중 하나라도 0이 아닐 때):
   
   2-1. Period > 0 (반복 펄스):
       - Delay 동안: 첫 번째 전압 레벨 (first_voltage)
       - Width 동안: 두 번째 전압 레벨 (second_voltage)
       - (Period - Delay - Width) 동안: 첫 번째 전압 레벨 (first_voltage)
       - 위 패턴을 Period 주기로 반복
   
   2-2. Period = 0 (단일 펄스):
       - Delay > 0인 경우:
         * Delay 동안: 첫 번째 전압 레벨 (first_voltage)
         * Width 동안: 두 번째 전압 레벨 (second_voltage)
         * 나머지 프레임: 첫 번째 전압 레벨 (first_voltage)
       - Delay = 0인 경우:
         * Width 동안만: 두 번째 전압 레벨 (second_voltage)
         * 나머지 프레임: 첫 번째 전압 레벨 (first_voltage)

3. SIG MODE에 따른 전압 레벨 결정:
   - MODE=0, INV=0: 모든 프레임에서 V1(Low), V2(High)
   - MODE=0, INV=1: Odd 프레임 V1(Low)/V2(High), Even 프레임 V2(Low)/V1(High)
   - MODE=1, INV=0: Odd 프레임 V1(Low)/V2(High), Even 프레임 V3(Low)/V4(High)
   - MODE=1, INV=1: Odd 프레임 V1(Low)/V2(High), Even 프레임 V4(Low)/V3(High)
"""

import numpy as np


class WaveformGenerator:
    """
    파형 생성 클래스
    
    Signal 객체의 파라미터를 입력받아 시간(Time)과 전압(Voltage) 배열을 생성합니다.
    """
    
    @staticmethod
    def generate_waveform(signal, num_frames, sync_data):
        """
        신호 파형 생성
        
        주어진 신호 정보와 프레임 수, SyncData를 기반으로 파형 데이터를 생성합니다.
        
        Args:
            signal (Signal): 파형을 생성할 신호 객체
            num_frames (int): 생성할 프레임 수
            sync_data (float): SyncData 값 (초 단위), 1 프레임의 길이
        
        Returns:
            tuple: (time_array, voltage_array)
                - time_array (np.array): 시간 축 데이터 (us 단위)
                - voltage_array (np.array): 전압 축 데이터 (V 단위)
        """
        # DC 출력 모드 체크 (Delay, Width, Period가 모두 0일 때)
        is_dc_mode = (signal.delay == 0 and signal.width == 0 and signal.period == 0)
        
        # 프레임 길이 = 1 SyncData
        # SyncData(초)를 신호 파라미터와 동일한 단위(us)로 변환
        frame_length = sync_data * 1000000  # 초 -> 마이크로초 변환
        
        total_length = frame_length * num_frames
        
        # 시간 배열 생성 (us 단위)
        # 해상도를 높여서 짧은 펄스도 잘 표현되도록 함
        time_points = 2000 * num_frames 
        time = np.linspace(0, total_length, time_points)
        voltage = np.zeros_like(time)
        
        # 각 프레임별로 파형 생성
        for frame_idx in range(num_frames):
            frame_start = frame_idx * frame_length
            frame_end = (frame_idx + 1) * frame_length
            
            # 현재 프레임에 해당하는 시간 인덱스 마스크
            frame_mask = (time >= frame_start) & (time < frame_end)
            frame_time = time[frame_mask]
            
            # 프레임 내 상대 시간 (0부터 frame_length까지)
            relative_time = frame_time - frame_start
            
            # 프레임 번호 (1부터 시작)
            frame_num = frame_idx + 1
            is_odd_frame = (frame_num % 2) == 1
            
            if is_dc_mode:
                # ========================================
                # DC 모드: Delay, Width, Period가 모두 0일 때
                # ========================================
                # 프레임 전체에 걸쳐 일정한 DC 전압 출력
                # SIG MODE와 INVERSION에 따라 프레임별 전압 결정
                dc_voltage = WaveformGenerator._get_dc_voltage(signal, is_odd_frame)
                frame_voltage = np.full_like(frame_time, dc_voltage)
            else:
                # ========================================
                # 일반 모드: SIG MODE에 따른 전압 레벨 결정
                # ========================================
                # first_voltage: 첫 번째 전압 레벨 (Delay 구간 및 펄스 OFF 구간)
                # second_voltage: 두 번째 전압 레벨 (Width 구간, 펄스 ON 구간)
                first_voltage, second_voltage = WaveformGenerator._get_voltage_levels(
                    signal, is_odd_frame
                )
                
                # 기본적으로 전체를 첫 번째 전압으로 초기화
                frame_voltage = np.full_like(frame_time, first_voltage)
                
                # ========================================
                # Period에 따른 파형 생성 분기
                # ========================================
                if signal.period > 0:
                    # ====================================
                    # 반복 펄스 모드 (Period > 0)
                    # ====================================
                    # 파형 패턴 (Period 주기로 반복):
                    #   1. Delay 동안: first_voltage (첫 번째 전압)
                    #   2. Width 동안: second_voltage (두 번째 전압)
                    #   3. (Period - Delay - Width) 동안: first_voltage
                    #   4. 위 패턴 반복
                    
                    # 각 시간 포인트가 Period 주기 내 어디에 위치하는지 계산
                    phase = relative_time % signal.period
                    
                    # Width 구간 판별: Delay 이후 ~ (Delay + Width) 이전
                    # 이 구간에서만 second_voltage 출력
                    high_mask = (phase >= signal.delay) & (phase < (signal.delay + signal.width))
                    frame_voltage[high_mask] = second_voltage
                    
                else:
                    # ====================================
                    # 단일 펄스 모드 (Period = 0)
                    # ====================================
                    # 파형 패턴:
                    #   - Delay > 0인 경우:
                    #     1. 0 ~ Delay: first_voltage (첫 번째 전압)
                    #     2. Delay ~ (Delay + Width): second_voltage (두 번째 전압)
                    #     3. (Delay + Width) ~ 프레임 끝: first_voltage
                    #   - Delay = 0인 경우:
                    #     1. 0 ~ Width: second_voltage (두 번째 전압만)
                    #     2. Width ~ 프레임 끝: first_voltage
                    
                    # Width 구간 시작/종료 시간
                    pulse_start = signal.delay
                    pulse_end = signal.delay + signal.width
                    
                    # Width 구간에만 second_voltage 출력
                    high_mask = (relative_time >= pulse_start) & (relative_time < pulse_end)
                    frame_voltage[high_mask] = second_voltage
                
            # 전체 전압 배열에 현재 프레임 데이터 할당
            voltage[frame_mask] = frame_voltage
        
        return time, voltage
    
    @staticmethod
    def _get_dc_voltage(signal, is_odd_frame):
        """
        DC 모드에서 프레임별 전압 결정
        (Delay, Width, Period가 모두 0일 때)
        
        Args:
            signal (Signal): 신호 객체
            is_odd_frame (bool): 홀수 프레임 여부
        
        Returns:
            float: 결정된 DC 전압 값
        """
        sig_mode = signal.sig_mode
        inversion = signal.inversion
        
        if sig_mode == 0:
            if inversion == 0:
                # MODE=0, INV=0: V1 DC 출력 (고정)
                return signal.v1
            else:
                # MODE=0, INV=1: Frame별 V1, V2 반복
                return signal.v1 if is_odd_frame else signal.v2
        
        elif sig_mode == 1:
            if inversion == 0:
                # MODE=1, INV=0: Frame별 V1, V3 반복
                return signal.v1 if is_odd_frame else signal.v3
            else:
                # MODE=1, INV=1: Frame별 V1, V4 반복
                return signal.v1 if is_odd_frame else signal.v4
        
        # 기본값
        return signal.v1
    
    @staticmethod
    def _get_voltage_levels(signal, is_odd_frame):
        """
        SIG MODE와 INVERSION에 따른 전압 레벨 결정 (일반 모드)
        
        Args:
            signal (Signal): 신호 객체
            is_odd_frame (bool): 홀수 프레임 여부
        
        Returns:
            tuple: (first_voltage, second_voltage) - 첫 번째 전압과 두 번째 전압
        """
        sig_mode = signal.sig_mode
        inversion = signal.inversion
        
        if sig_mode == 0:
            # MODE 0: V1, V2 사용
            if inversion == 0:
                # Frame별 반전 없음: 항상 V1(Low), V2(High)
                return signal.v1, signal.v2
            else:
                # Frame별 반전 적용
                if is_odd_frame:
                    return signal.v1, signal.v2
                else:
                    return signal.v2, signal.v1
        
        elif sig_mode == 1:
            # MODE 1: Odd/Even Frame별 다른 전압 사용
            if is_odd_frame:
                # Odd Frame: V1, V2 사용
                return signal.v1, signal.v2
            else:
                # Even Frame: V3, V4 사용
                if inversion == 0:
                    # V3(Low), V4(High)
                    return signal.v3, signal.v4
                else:
                    # V4(Low), V3(High) - 순서 반전
                    return signal.v4, signal.v3
        
        # 기본값
        return signal.v1, signal.v2
    
    @staticmethod
    def get_voltage_range(signals):
        """
        모든 신호의 전압 범위 계산
        
        그래프의 Y축 범위를 설정하거나 오토스케일링에 사용됩니다.
        
        Args:
            signals (list): Signal 객체 리스트
        
        Returns:
            tuple: (min_voltage, max_voltage)
        """
        if not signals:
            return 0.0, 5.0
        
        all_voltages = []
        for signal in signals:
            all_voltages.extend([signal.v1, signal.v2, signal.v3, signal.v4])
        
        return min(all_voltages), max(all_voltages)
