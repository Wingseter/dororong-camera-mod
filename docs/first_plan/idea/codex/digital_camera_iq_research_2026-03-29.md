# DC23 디지털 카메라 화질 개선 연구 메모

> 작성일: 2026-03-29
> 대상: Generalplus GP1235 기반 DC23
> 범위: 카메라 단독 사용 기준의 화질 개선
> 제외: Mac/PC 후처리, 외부 AI 복원, 호스트 실시간 파이프라인

## 범위 수정

이 문서는 이전의 호스트 소프트웨어 중심 복원 메모와 다르게, **DC23 자체가 더 좋은 디지털 카메라가 되도록 만드는 방향**에만 집중한다.  
즉, 관심 영역은 다음 네 단계다.

1. 센서 입력
2. ISP 처리
3. JPEG/MJPEG 인코딩
4. 저장되는 사진/동영상 결과물

## 한줄 결론

이 카메라의 화질을 가장 크게 올리는 길은 "촬영 후 보정"이 아니라, **펌웨어에서 native 해상도, AE/AWB/gamma/CCM, denoise/sharpen, JPEG Q-table, 장면별 preset 로직을 다시 튜닝하는 것**이다.

참고: 아래의 우선순위와 설계 제안은 내부 분석 결과와 외부 논문/공식 자료를 결합한 **프로젝트 수준의 추론**이다.

## 1. 현재 확정된 사실

내부 분석 문서를 기준으로 이미 확보된 사실은 다음과 같다.

- SD 카드 기반 커스텀 펌웨어 업그레이드가 성공했다.
- GP1235 계열 펌웨어는 바이트 패치뿐 아니라 설정/리소스 수정까지 반복 배포할 수 있다.
- 메뉴 문자열 기준으로 이미 여러 ISP 파라미터가 구현되어 있다.
- 메뉴에 영상 해상도 `1080P / 720P / VGA`, 사진 해상도 `12M / 8M / 2M / 1M / VGA`가 존재한다.
- 메뉴에 Brightness, Exposure, White Balance, Sharpness, Colour, Saturation, EV 보정이 존재한다.
- Generalplus 동계열 공개 자료 기준, SoC는 144MHz ARM7TDMI와 하드웨어 ISP, JPEG CODEC, scaling engine, programmable up-scaling을 가진다.
- 공식 GPCV2247F 페이지는 **embedded ISP supports raw data sensor up to 720p** 라고 명시한다.

여기서 바로 중요한 추론이 나온다.

- **강한 추론**: 이 카메라의 1080P 영상 모드와 12M/8M 사진 모드는 true sensor-native가 아니라 scaler/interpolation 경로일 가능성이 매우 높다.
- 이유: 공개된 동계열 ISP 입력 상한이 720p이고, 별도 scaling engine/up-scaling 기능이 공식적으로 존재하기 때문이다.

즉, 이 프로젝트의 첫 번째 목표는 "더 큰 숫자"가 아니라 **더 좋은 실제 정보량**이어야 한다.

## 2. 외부 연구가 시사하는 방향

### 2.1 ISP는 고정값 몇 개 바꾸는 수준이 아니라 전체 파이프라인 최적화 문제다

`Hardware-in-the-Loop End-to-End Optimization of Camera Image Processing Pipelines` (CVPR 2020)는  
카메라 ISP 품질이 서로 얽힌 여러 하이퍼파라미터의 결과이며, 수작업 감으로 맞추는 것보다 **실제 하드웨어를 돌리면서 목적 함수를 두고 최적화하는 방식**이 더 낫다고 보여줬다.

이 프로젝트에 대한 의미:

- Brightness만 바꾸고 끝내면 안 된다.
- AE target, gamma, sharpen, denoise, saturation, color matrix, JPEG quality는 함께 조정해야 한다.
- 결국 가장 강한 방법은 **펌웨어 버전별 촬영 결과를 실제 차트와 장면으로 측정하면서 튜닝하는 것**이다.

### 2.2 고정된 ISP보다 장면별/목적별 ISP가 유리하다

`ReconfigISP` (ICCV 2021)는 장면과 목적에 따라 ISP 구조/파라미터가 달라져야 함을 보여줬고,  
`DynamicISP` (ICCV 2023)는 classical ISP functions를 동적으로 제어해도 저비용으로 큰 이득을 낼 수 있음을 보였다.

이 카메라에 대한 의미:

- 하나의 만능 preset만 만드는 것은 비효율적이다.
- 이 카메라에는 이미 `Automatic / Motion / Night View`, 여러 WB preset, Sharp/Standard/Soft 같은 메뉴 분기가 있다.
- 따라서 최적 전략은 **단일 global 튜닝**이 아니라 **Daylight / Indoor / Night / Motion 같은 목적형 프로파일 튜닝**이다.

즉, 이 프로젝트의 산출물은 "하나의 최고값"보다 다음에 가깝다.

- 최고의 주간 동영상 preset
- 최고의 실내 동영상 preset
- 최고의 야간 동영상 preset
- 최고의 스틸 이미지 preset

### 2.3 디지털 카메라 화질 저하는 ISP 오설정에서 많이 나온다

`Learning Degradation-Independent Representations for Camera ISP Pipelines` (CVPR 2024)은  
카메라 ISP 출력이 sensor noise, demosaicing noise, compression artifacts, 그리고 잘못된 ISO/gamma 같은 ISP 설정 때문에 쉽게 품질이 무너진다고 정리한다.

이 카메라에 대한 의미:

우선순위는 명확하다.

1. 노출/게인 정책
2. 화이트밸런스와 색 재현
3. gamma / tone curve
4. denoise / sharpen 균형
5. JPEG 압축 강도

이 다섯 개가 실제 사진과 영상의 인상을 가장 크게 좌우한다.

### 2.4 WB는 단순 정확도보다 "좋아 보이는 색"도 중요하다

`Learning Camera-Agnostic White-Balance Preferences` (ICCVW 2025)는  
상용 카메라의 AWB는 단순한 neutral correction이 아니라 **미적으로 선호되는 색**을 목표로 하는 경우가 많다고 설명한다.

이 카메라에 대한 의미:

- WB는 "회색을 중립으로 맞춘다"로 끝나지 않는다.
- 싼 카메라일수록 indoor 조명에서 녹색/황색 틴트가 크게 뜰 가능성이 있다.
- 따라서 DC23에서는 WB 정확도뿐 아니라 **주광 / 형광등 / 텅스텐에서 사람이 보기 좋은 skin tone과 흰색 유지**를 같이 봐야 한다.

### 2.5 확대는 RGB 결과물을 키우는 것보다 카메라 파이프라인 안에서 다루는 편이 낫다

`Learning To Zoom Inside Camera Imaging Pipeline` (CVPR 2022)은  
카메라 파이프라인 안쪽에서 다루는 zoom/super-resolution이 RGB 결과물 이후의 업샘플보다 더 적절하다는 방향을 보여준다.

이 카메라에 대한 의미는 조금 다르다.

- GP1235급 SoC에서 복잡한 learned zoom을 돌릴 수는 없다.
- 하지만 원칙은 동일하다.
- **후단 RGB upscale보다 native sensor 경로와 내부 scaler/ISP 정책이 더 중요하다.**

즉, DC23에서는 "1080P 숫자 유지"보다 **native 해상도에서 가장 정보량이 높은 결과물**을 내는 쪽이 맞다.

## 3. 디지털 카메라로서 우선 개선해야 할 것

### 3.1 1순위: 가짜 해상도보다 진짜 디테일

가장 먼저 검증해야 할 것은 아래 두 개다.

1. 1080P 영상 모드가 실제 센서 정보를 늘리는지
2. 12M / 8M 사진 모드가 실제 디테일을 늘리는지

현재 근거로는 둘 다 회의적이다.

- 동계열 공식 ISP 입력 상한은 720p
- 펌웨어는 scaling engine과 up-scaling 기능을 가진다
- 저가 카메라 메뉴의 고해상도 스틸 모드는 종종 interpolation이다

따라서 **강한 추론**으로는:

- 동영상의 true-quality 기본값은 720P일 가능성이 높다.
- 스틸 이미지의 true-quality 기본값은 2M 또는 sensor-native 모드일 가능성이 높다.

이 프로젝트의 첫 실험은 "어떤 숫자가 가장 큰가"가 아니라 **어떤 모드가 실제 MTF와 디테일이 가장 좋은가**를 찾는 것이다.

### 3.2 2순위: AE/게인 정책 재설계

저가 카메라 화질을 망치는 가장 흔한 원인은 과도한 게인과 어두운 tone policy다.

조정 대상:

- AE target brightness
- analog gain 우선 / digital gain 후순위 정책
- integration time 상한
- motion blur와 noise 간 트레이드오프
- Night View / Motion 모드의 실제 동작 차이

목표:

- 밝기 확보를 위해 무작정 gain을 밀지 않기
- 가능한 한 analog gain과 exposure를 먼저 쓰고, digital gain은 제한
- 야간에는 밝기보다 노이즈와 blur 균형을 맞추기

### 3.3 3순위: AWB / CCM / gamma

사람이 "좋다"고 느끼는 카메라 화질은 해상도뿐 아니라 색에서 크게 갈린다.

핵심 항목:

- AWB bias
- daylight / cloudy / tungsten / fluorescent preset의 실제 gain 값
- Color Correction Matrix
- gamma curve
- saturation 기본값

실제 목표:

- 피부톤이 누렇게 뜨지 않기
- 흰 벽과 종이가 초록/파랑으로 틀어지지 않기
- 암부가 뭉개지지 않으면서 중간톤이 죽지 않기

이 카메라에서 큰 체감 개선은 오히려 super-sharp보다 **WB + gamma + CCM** 에서 나올 가능성이 높다.

### 3.4 4순위: denoise / sharpen 밸런스

싼 카메라는 보통 두 가지 방식 중 하나로 망가진다.

- 노이즈를 막으려다 너무 뭉개짐
- 선명해 보이게 하려다 halo와 edge ringing이 심해짐

따라서 최적점은 "더 샤프"가 아니라:

- 저주파 노이즈는 줄이고
- 실제 edge는 살리고
- halo와 가짜 윤곽은 줄이는 지점

조정 대상:

- ISP denoise strength
- sharpen strength
- bad-pixel cancellation threshold
- colour/saturation 과다 보정 여부

### 3.5 5순위: JPEG / MJPEG 인코더 품질

이 카메라에서 저장되는 결과물은 결국 JPEG 계열 품질에 크게 묶인다.

핵심 포인트:

- still photo Q-table
- MJPEG Q-table
- High / Standard / Economy mapping
- frame buffer / bitrate / write budget

내부 분석상 현재 720p30에서 프레임당 평균 용량은 아직 여유가 큰 편이다.  
따라서 초기 가설로는 **현재 품질보다 더 낮은 양자화 값으로 가도 저장 대역폭에 아직 공간이 있을 가능성**이 높다.

즉, 실제 화질 향상을 위해 가장 현실적인 고효율 작업은:

1. still photo를 무조건 High quality 기본값으로 만들기
2. video MJPEG Q-table을 한 단계 올리기
3. Economy/Standard를 덜 공격적으로 만들기

## 4. 이 카메라에서 가장 유망한 연구 트랙

### 4.1 Track A: sensor-native truth 찾기

가장 먼저 확정해야 할 질문:

- 센서 모델은 무엇인가
- 센서의 native 출력 해상도는 무엇인가
- 1080P/12M 메뉴가 실제 센서 정보를 반영하는가

이 트랙이 중요한 이유:

- 이후 모든 튜닝의 기준점이 정해진다.
- fake resolution을 개선하려고 시간을 쓰는 실수를 줄인다.

권장 실험:

- 해상도별 차트 촬영 후 MTF50 비교
- 파일 크기, JPEG 구조, edge detail, aliasing 비교
- 필요 시 센서 I2C init sequence로 native mode 확인

### 4.2 Track B: still image 우선 튜닝

디지털 카메라로서 가장 즉각적인 결과는 스틸 이미지에서 드러난다.

권장 순서:

1. photo mode 기본 해상도를 true-quality 모드로 재설정
2. photo quality 기본값을 High로 변경
3. WB preset / gamma / saturation / sharpness를 스틸 기준으로 조정
4. JPEG Q-table을 사진 우선으로 재튜닝

핵심 판단:

- 이 카메라를 "사진이 생각보다 괜찮은 장난감 카메라"로 만드는 가장 빠른 길은 스틸 튜닝이다.
- 동영상보다 프레임레이트 제약이 덜하므로 JPEG quality를 더 공격적으로 올릴 수 있다.

### 4.3 Track C: video mode를 진짜 720p 카메라로 만들기

동영상 개선은 "1080P처럼 보이게"보다 **좋은 720P 카메라**를 만드는 방향이 맞다.

핵심 작업:

- 720P 모드 화질 최적화
- Motion / Night View 내부 파라미터 차이 추적
- MJPEG Q-table 상향
- denoise/sharpen 밸런스 재조정
- flicker 방지용 PAL/anti-flicker 기본값 검토

목표:

- 디테일이 살아 있는 720P
- 블록 노이즈가 적은 MJPEG
- 과한 halo 없는 edge
- 실내 조명에서 색이 덜 깨지는 video

### 4.4 Track D: 장면별 preset firmware

외부 연구 흐름상, 고정된 하나의 ISP보다 장면별 preset이 더 맞다.

권장 preset 구조:

- `Photo Best`
- `Video Day`
- `Video Indoor`
- `Video Night`
- `Motion Priority`

각 preset에서 따로 잡아야 할 값:

- exposure mode
- gain ceiling
- gamma
- saturation
- sharpen / denoise
- JPEG quality
- WB bias

이 방식은 GP1235의 연산 제약에도 맞고, 실제 체감 화질도 크게 올릴 가능성이 있다.

### 4.5 Track E: sensor-specific tuning

결국 최고 화질의 끝은 센서 레벨까지 내려가야 나온다.

찾아야 할 것:

- 센서 ID
- analog gain register
- digital gain register
- exposure register
- black level / color gain / mirror-flip 관련 register
- test pattern enable register

센서가 확인되면 가능한 개선:

- 저조도 gain 정책 수정
- 색 재현 개선
- clipping / black crush 완화
- 노이즈와 blur 타협점 개선

## 5. 실험 방법론

### 5.1 수동 감상이 아니라 hardware-in-the-loop 튜닝

이 프로젝트는 "보기에 괜찮다"만으로 가면 재현성이 없다.  
가장 좋은 방식은 논문에서 제안하듯, 실제 카메라 출력 결과를 점수화해서 펌웨어를 반복 탐색하는 것이다.

권장 측정 항목:

- MTF50 / slanted-edge sharpness
- ColorChecker Delta E
- gray patch noise sigma
- clipping ratio
- dark patch black crush
- JPEG file size
- low-light shutter blur

권장 장면 세트:

- 실외 주광
- 실내 형광등
- 실내 텅스텐
- 저조도
- 피부톤
- 잔패턴
- 역광

### 5.2 펌웨어 실험 순서

1. native resolution truth test
2. still image Q-table test
3. video MJPEG Q-table test
4. WB / gamma / saturation test
5. denoise / sharpen test
6. exposure/gain policy test
7. preset 분기 test
8. sensor register diff 추적

이 순서가 좋은 이유:

- 먼저 fake resolution 문제를 정리해야 이후 데이터 해석이 깨지지 않는다.
- 그 다음으로는 인코딩과 톤/색 조정이 가장 큰 체감 화질을 만든다.

## 6. 지금 시점의 최우선 연구 과제

가장 먼저 할 과제 다섯 개를 좁히면 아래와 같다.

1. **1080P / 12M / 8M가 진짜 해상도인지 검증**
2. **still photo용 JPEG Q-table 위치와 매핑 찾기**
3. **settings block의 체크섬 규칙 해독**
4. **sensor init I2C 시퀀스에서 센서 모델 식별**
5. **AWB/CCM/gamma 초기화 코드 찾기**

이 다섯 개가 풀리면, 이 카메라는 단순한 UVC 장난감이 아니라 **튜닝 가능한 디지털 카메라 플랫폼**으로 바뀐다.

## 7. 최종 판단

디지털 카메라로서의 DC23 화질 개선은 세 줄로 요약된다.

1. **큰 숫자 해상도를 버리고 true-quality native 모드를 찾는다.**
2. **AE/AWB/gamma/CCM/denoise/sharpen/JPEG를 카메라 내부에서 다시 튜닝한다.**
3. **하나의 만능 세팅보다 장면별 preset firmware로 간다.**

이 방향이 가장 현실적이고, 실제 결과물의 체감 개선도 가장 크다.  
특히 이 카메라에서는 host AI보다 **native 해상도 진실화 + ISP 재튜닝 + JPEG 품질 상향**이 훨씬 직접적인 화질 개선이다.

## 내부 참고 문서

- `docs/ongoing/firmware_analysis.md`
- `docs/ongoing/ghidra_deep_analysis.md`
- `docs/ongoing/additional_findings.md`
- `docs/ongoing/sd_upgrade_success.md`
- `docs/research_isp_capabilities.md`

## 외부 참고 자료

1. Generalplus GPCV2247F product page  
   https://www.generalplus.com/GPCV2247F-rdLSC-phLVNG2jLN5006SVpnSNproduct_detail

2. Hardware-in-the-Loop End-to-End Optimization of Camera Image Processing Pipelines, CVPR 2020  
   https://openaccess.thecvf.com/content_CVPR_2020/html/Mosleh_Hardware-in-the-Loop_End-to-End_Optimization_of_Camera_Image_Processing_Pipelines_CVPR_2020_paper.html

3. ReconfigISP: Reconfigurable Camera Image Processing Pipeline, ICCV 2021  
   https://openaccess.thecvf.com/content/ICCV2021/html/Yu_ReconfigISP_Reconfigurable_Camera_Image_Processing_Pipeline_ICCV_2021_paper.html

4. DynamicISP: Dynamically Controlled Image Signal Processor for Image Recognition, ICCV 2023  
   https://openaccess.thecvf.com/content/ICCV2023/html/Yoshimura_DynamicISP_Dynamically_Controlled_Image_Signal_Processor_for_Image_Recognition_ICCV_2023_paper.html

5. Learning Degradation-Independent Representations for Camera ISP Pipelines, CVPR 2024  
   https://openaccess.thecvf.com/content/CVPR2024/html/Guo_Learning_Degradation-Independent_Representations_for_Camera_ISP_Pipelines_CVPR_2024_paper.html

6. Learning To Zoom Inside Camera Imaging Pipeline, CVPR 2022  
   https://openaccess.thecvf.com/content/CVPR2022/html/Tang_Learning_To_Zoom_Inside_Camera_Imaging_Pipeline_CVPR_2022_paper.html

7. Learning Camera-Agnostic White-Balance Preferences, ICCVW 2025  
   https://openaccess.thecvf.com/content/ICCV2025W/MIPI/html/Zhao_Learning_Camera-Agnostic_White-Balance_Preferences_ICCVW_2025_paper.html
