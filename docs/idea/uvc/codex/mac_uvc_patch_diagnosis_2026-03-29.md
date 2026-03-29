# macOS에서 UVC 패치가 잘 적용되지 않는 이유와 해결 방향

> 작성일: 2026-03-29
> 범위: DC23의 UVC 패치가 왜 Mac에서 검증/적용이 어렵고, 어떻게 풀 수 있는지 정리

## 한줄 결론

현재 UVC 패치는 **디스크립터 광고만 바꾼 상태**에 가깝고, 실제 UVC control transaction과 ISP 반영 코드가 따라오지 않기 때문에 실효가 거의 없다.  
게다가 macOS는 기본 UVC 카메라를 Core Media I/O class-compliant extension 경로로 붙이기 때문에, **Mac은 지금 상태의 UVC 패치를 검증하는 1차 환경으로도 좋지 않다.**

즉, 문제는 두 겹이다.

1. 카메라 펌웨어 내부에 진짜 UVC control handler가 부족하다.
2. macOS 기본 UVC 스택은 저수준 UVC 상태를 직접 보기 어렵게 만든다.

## 1. 현재까지 관측된 증상

내부 문서 기준 현재 확인된 현상은 아래와 같다.

- `bmControls`를 `0x01 -> 0x3F`로 바꾸면 Windows 쪽에서는 채도/선명도 같은 UI가 나타난다.
- 하지만 조절해도 실제 화면 변화는 없다.
- Brightness default 값 패치도 실효가 없었다.
- macOS에서는 720p 직접 요청이 실패하고 기본값으로 fallback되며, 1080p는 잡히지만 실제로는 업스케일된 결과로 보인다.
- 원래 장치의 UVC 노출은 Brightness 위주로 극히 제한적이고, Extension Unit도 없다.

이 관측은 한 방향을 강하게 가리킨다.

- **강한 추론**: 현재 패치는 "호스트에게 지원한다고 말만 하는 상태"이고, 실제로는 SET_CUR/GET_CUR 요청을 처리해 ISP 상태를 바꾸는 경로가 충분히 구현되어 있지 않다.

## 2. 외부 공식 자료가 말하는 핵심 사실

### 2.1 UVC control은 비트만 켜서는 안 되고, 실제 GET/SET 요청이 지원돼야 한다

Linux UVC 공식 문서는 저수준 UVC control을 질의할 때 먼저 `UVC_GET_INFO`로 GET/SET 지원 여부를 확인해야 하며,  
그 다음 `UVC_GET_CUR`, `UVC_GET_MIN`, `UVC_GET_MAX`, `UVC_GET_DEF`, `UVC_GET_RES`, `UVC_SET_CUR` 같은 요청을 써야 한다고 설명한다.

이 말은 곧:

- `bmControls` 비트가 켜져 있어도
- 실제로 해당 control selector에 대한 GET/SET 응답이 없거나
- 값이 ISP 상태와 연결되지 않으면

호스트에서 보여주는 UI는 그냥 빈 껍데기가 될 수 있다는 뜻이다.

### 2.2 macOS는 기본 UVC 카메라를 class-compliant CMIO extension으로 붙인다

Apple Core Media I/O 문서는 macOS 12.3부터 USB 카메라를 위한 class-compliant CMIO extension을 시스템이 기본 제공한다고 설명한다.  
또한 기본 USB video class extension의 매칭을 override해서 **custom DriverKit + CMIO extension** 으로 대체할 수 있다고 명시한다.

이게 의미하는 바는 분명하다.

- Mac에서 UVC 카메라는 단순한 "raw USB 장치"로만 보이지 않는다.
- 시스템 기본 camera stack이 한 번 끼어든다.
- 따라서 펌웨어의 UVC descriptor/control 변화가 그대로 앱에 노출되지 않을 수 있다.

### 2.3 macOS 앱 레벨은 AVFoundation 추상화 위에서 동작한다

Apple `AVCaptureDevice` 문서는 카메라 접근과 설정을 AVFoundation의 `AVCaptureDevice` 기반으로 설명하고,  
노출/화이트밸런스/포커스/포맷 같은 속성을 중심으로 다룬다.

이 문서 구조 자체가 시사하는 것은 다음이다.

- macOS 표준 앱과 일반 AVFoundation 경로는 "generic UVC PU slider"를 직접 보여주는 체계가 아니다.
- Brightness / Saturation / Sharpness 같은 UVC PU control을 펌웨어가 조금 바꿨다고 해서, Mac의 카메라 앱이 곧바로 그 의미를 그대로 드러내리라고 기대하기 어렵다.

이 부분은 Apple 문서의 노출 방식과 현재 실측 결과를 결합한 **추론**이다.

### 2.4 FFmpeg avfoundation은 AVFoundation이 지원하는 형식만 요청할 수 있다

FFmpeg 공식 문서는 avfoundation 입력에서 `-video_size`, `-pixel_format`, `-framerate`를 요청할 수 있지만,  
지원되지 않는 형식을 지정하면 장치가 지원하는 목록 중 첫 번째 형식으로 fallback될 수 있다고 설명한다.

따라서 현재 macOS에서 보인:

- 720p 직접 요청 실패
- 기본값 fallback
- 1080p는 잡히지만 실제로는 업스케일처럼 보이는 현상

은 "카메라 UVC descriptor의 진실"과 "AVFoundation이 노출하는 형식"이 어긋나 있다는 신호로 해석하는 편이 맞다.

## 3. 현재 패치가 실효가 없는 직접 원인

### 3.1 `bmControls` 패치는 descriptor-only 패치다

`bmControls`는 "이 control이 있습니다"라고 광고하는 비트맵이다.  
하지만 진짜 작동하려면 최소한 아래가 모두 필요하다.

- 해당 selector에 대한 GET/SET 요청 수신
- MIN/MAX/DEF/RES 값 제공
- 현재값 저장
- 저장된 값을 실제 ISP 파라미터에 반영

현재 결과를 보면 이 네 단계 중 마지막 둘, 혹은 전부가 빠져 있을 가능성이 높다.

즉:

- Windows UI가 보이는 것 = descriptor advertising은 먹음
- 화면이 안 바뀌는 것 = actual control path는 안 먹음

### 3.2 Brightness default 패치는 런타임 경로가 아닐 가능성이 높다

`0x08279C`, `0x08279E`를 바꿨는데 효과가 없었다는 것은 크게 세 가지 가능성을 뜻한다.

1. 그 값은 descriptor 응답용 테이블일 뿐, 실제 ISP current state는 다른 곳에서 초기화된다.
2. host가 `GET_DEF`를 안 쓰거나, 기본값을 읽어도 장면 시작 시 다시 AE가 덮어쓴다.
3. Brightness control은 존재하더라도 실제 카메라의 auto exposure / gain 루프가 더 상위에서 화면을 결정한다.

현재 증상상 1번과 3번 조합일 가능성이 높다.

### 3.3 Mac은 지금 상태의 패치를 검증하기에 너무 상위 레벨이다

Mac에서 지금 바로 검증이 어려운 이유는 단순하다.

- 표준 경로가 AVFoundation/CMIO 기반이다.
- 일반 앱은 저수준 UVC request/response를 직접 보여주지 않는다.
- 포맷도 AVFoundation이 노출하는 형태로 보인다.

그래서 Mac에서는 아래 두 질문에 바로 답하기 어렵다.

- 장치가 정말 `GET_CUR/SET_CUR`를 제대로 처리하는가
- descriptor 수정이 OS camera stack에 어떤 형태로 반영됐는가

즉, **Mac은 증상을 보기엔 좋지만 원인을 확정하기엔 불리한 환경**이다.

### 3.4 보조 가설: 동일 VID/PID + 무시리얼이 반복 테스트를 흐릴 수 있다

이 장치는 serial number가 없다.  
따라서 같은 VID/PID, 같은 product string으로 반복 실험하면 macOS 쪽에서 재열거/재해석이 불명확하게 보일 수 있다.

이 부분은 외부 공식 문서로 직접 확인한 사실은 아니고, 현재 장치 조건과 USB 일반 동작을 결합한 **저신뢰 추론**이다.  
하지만 실험 전략 차원에서는 충분히 고려할 가치가 있다.

## 4. "진짜 UVC 지원"이 되려면 펌웨어에서 무엇이 더 있어야 하나

현재처럼 descriptor만 바꾸는 단계로는 부족하다.  
실제로 동작시키려면 다음이 필요하다.

### 4.1 Control selector별 request handler

최소 지원 세트:

- `GET_INFO`
- `GET_CUR`
- `GET_MIN`
- `GET_MAX`
- `GET_DEF`
- `GET_RES`
- `SET_CUR`

이 응답들이 control별 타입과 길이에 맞게 일관되게 나와야 한다.

### 4.2 Runtime state 저장소

각 control마다 현재값이 있어야 한다.

예:

- brightness_current
- saturation_current
- sharpness_current
- wb_temp_current
- gain_current

그리고 이 값이 UVC 응답에만 존재하면 안 되고, 실제 카메라 파이프라인과 연결돼야 한다.

### 4.3 ISP 반영 코드

실질적으로 중요한 부분은 여기다.

- Brightness -> ISP luminance offset 또는 AE target
- Saturation -> color matrix / saturation coefficient
- Sharpness -> edge enhancement strength
- Gamma -> gamma LUT 또는 preset selector
- Gain -> analog/digital gain policy

즉, UVC path는 결국 ISP register 또는 설정 블록을 건드리는 함수로 이어져야 한다.

### 4.4 Descriptor와 implementation의 일치

광고한 control만 지원해야 한다.  
반대로 구현된 control이면 descriptor에도 정확히 반영해야 한다.

불일치가 생기면:

- 어떤 OS는 UI만 보여주고
- 어떤 OS는 조용히 무시하고
- 어떤 OS는 협상 자체를 이상하게 할 수 있다

## 5. macOS에서 계속 가려면 가능한 해결 경로

### 5.1 가장 현실적인 경로: UVC를 주 화질 개선 경로로 쓰지 않는다

현재 프로젝트의 핵심 목적이 카메라 자체 화질 개선이라면,  
UVC는 compatibility layer 정도로 두고 화질 개선의 본체는 **카메라 독립 모드의 ISP/JPEG 튜닝** 으로 두는 편이 맞다.

이 경로의 장점:

- Mac camera stack 제약을 피한다
- 저장 결과물 화질을 직접 올릴 수 있다
- UVC control 구현 부담이 줄어든다

### 5.2 UVC를 계속 하려면 Linux를 1차 진실 환경으로 쓴다

공식 문서 관점에서 가장 잘 맞는 검증 환경은 Linux `uvcvideo` 쪽이다.

이유:

- 저수준 UVC control query 흐름이 문서화돼 있다
- `GET_INFO`, `GET_CUR`, `SET_CUR` 같은 실제 transaction을 더 직접 검증할 수 있다
- descriptor advertising과 real handler를 분리해서 보기 좋다

실질적 전략:

1. Linux에서 selector별 `GET_INFO/GET_CUR/SET_CUR`가 진짜로 되는지 확인
2. 그 다음 Windows에서 UI 노출 확인
3. 마지막에 Mac 호환성을 본다

즉, **Mac을 1차 검증 환경으로 쓰지 않는 것**이 중요하다.

### 5.3 Mac에서 꼭 제대로 쓰려면 custom CMIO/DriverKit extension 경로가 있다

Apple 공식 문서는 기본 USB video class extension을 override할 수 있다고 명시한다.  
따라서 Mac에서 정말 원하는 방식으로 이 카메라를 다루고 싶다면:

- DriverKit extension으로 기본 매칭을 끊고
- custom CMIO extension을 올려
- 앱에는 원하는 포맷/컨트롤을 가진 camera device로 노출

하는 길이 열려 있다.

이 경로의 의미:

- 기본 UVC driver의 해석에 끌려가지 않는다
- Mac 앱에 원하는 포맷/제어 정책을 안정적으로 노출할 수 있다
- 단, 구현 난이도는 매우 높다

즉, 이건 "펌웨어만으로 해결"이 아니라 **Mac용 드라이버/카메라 확장 프로젝트**가 된다.

### 5.4 Mac에서 최소한으로 할 수 있는 현실적 테스트

Mac에서 당장 할 수 있는 검증은 아래 정도다.

1. FFmpeg avfoundation `-list_formats`로 AVFoundation이 보는 형식 확인
2. 작은 AVFoundation 도구로 `AVCaptureDevice.formats` 열거
3. 패치 전후 VID/PID/bcdDevice를 바꿔 재열거 차이 확인
4. 앱이 아니라 시스템이 보는 장치 속성 변화를 비교

이 테스트는 "진짜 UVC control 동작" 확인용이라기보다 **Mac stack이 무엇을 보고 있는지 확인**하는 용도다.

## 6. 문제별 해결책 정리

### 문제 1. UI는 뜨는데 화면이 안 바뀜

원인:

- descriptor만 바뀌고 handler/ISP 반영이 없음

해결:

- selector별 GET/SET 처리 구현
- runtime state와 ISP 반영 코드 연결

### 문제 2. Brightness default 패치가 안 먹음

원인:

- 실제 current state 초기화 위치가 다르거나 AE가 덮어씀

해결:

- descriptor table이 아닌 런타임 ISP 초기화 코드/설정 블록을 찾아 수정
- 필요하면 AE target 자체를 조정

### 문제 3. Mac에서 720p 검증이 안 됨

원인:

- AVFoundation이 장치 원시 descriptor와 다른 형태로 format을 노출하거나 fallback 처리

해결:

- Mac은 1차 진실 환경으로 쓰지 않기
- Linux에서 descriptor/control 진실을 먼저 확정
- Mac은 호환성 확인 단계로만 사용

### 문제 4. Mac에서 generic UVC controls가 잘 안 보임

원인:

- AVFoundation/CMIO 경로가 generic PU slider 중심이 아님

해결:

- custom Mac app 또는 custom CMIO extension 필요
- 아니면 UVC generic controls에 집착하지 말고 카메라 내부 기본값 자체를 더 좋게 만들기

## 7. 권장 다음 단계

우선순위를 줄이면 아래 순서가 맞다.

1. **UVC descriptor patch만으로는 부족하다는 점을 확정하고, actual control handler 역분석으로 넘어간다.**
2. **Brightness current/default의 진짜 런타임 소스를 찾는다.**
3. **UVC 검증 1차 환경을 Linux로 옮긴다.**
4. **Mac은 avfoundation format enumeration과 호환성 확인용으로만 쓴다.**
5. **프로젝트 주력은 여전히 standalone camera ISP/JPEG 튜닝에 둔다.**

## 최종 판단

지금 UVC가 Mac에서 잘 안 되는 이유는 "Mac이 이상해서"가 아니라,  
**카메라 쪽 구현이 descriptor-only에 머물러 있고, Mac 쪽은 그 위에 class-compliant camera stack이 한 겹 더 있기 때문**이다.

따라서 해결 방향도 분명하다.

- 단기: Mac에서 UVC를 주 검증 환경으로 쓰지 않는다
- 중기: 실제 UVC request handler와 ISP 연결을 구현한다
- 장기: Mac에서 정말 제어권이 필요하면 custom CMIO/DriverKit extension으로 간다

이게 현재 관측과 공식 문서를 동시에 만족하는 가장 일관된 설명이다.

## 내부 참고 문서

- `docs/first_plan/phase1_quick_wins.md`
- `docs/mac_analysis_report.md`
- `UVC_Controls_Research.md`

## 외부 참고 자료

1. Linux UVC driver documentation  
   https://docs.kernel.org/userspace-api/media/drivers/uvcvideo.html

2. Apple Core Media I/O overview  
   https://developer.apple.com/documentation/coremediaio

3. Apple: Creating a camera extension with Core Media I/O  
   https://developer.apple.com/documentation/coremediaio/creating-a-camera-extension-with-core-media-i-o

4. Apple: Overriding the default USB video class extension  
   https://developer.apple.com/documentation/coremediaio/overriding-the-default-usb-video-class-extension

5. Apple `AVCaptureDevice` documentation  
   https://developer.apple.com/documentation/avfoundation/avcapturedevice

6. FFmpeg devices documentation (`avfoundation`)  
   https://ffmpeg.org/ffmpeg-devices.html
