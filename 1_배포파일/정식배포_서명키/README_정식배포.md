# 정식배포 폴더 안내 (2026-09-07)

## 들어 있는 것
- `todak-release.keystore` — **앱 서명 키(도장)**. 이후 모든 정식 업데이트는 이 키로 서명해야 기존 설치 위에 덮어 설치됩니다.
  - 비밀번호·별칭은 `유방암\_키모음.env` 맨 아래(ANDROID_KEYSTORE_*)에 있습니다.
  - **분실하면 참여자 전원이 앱을 지우고 다시 깔아야 합니다.** 이 폴더째 백업해 두세요 (USB 등 오프라인 사본 권장).
- `토닥_v0.9_정식서명판.apk` — 위 키로 서명한 릴리스 빌드(64비트+32비트 ARM, 33MB).
- 빌드용 사본: `todak-app/android/todak-release.keystore` (한글 경로에서 Gradle이 키를 못 읽어 복사해 둠 — 두 파일은 같은 키). 이 APK가 참여자 배포용 형식의 첫 후보입니다.

## 시험판과 정식판의 차이
| | 시험판 (`유방암\토닥_vX.Y_시험판.apk`) | 정식판 (이 폴더) |
|---|---|---|
| 서명 | 개발용 임시 키 | 연구용 정식 키 |
| 덮어 설치 | 시험판끼리만 가능 | 정식판끼리만 가능 |
| 용도 | 교수님·연구팀 시험 | 참여자 배포 |

⚠ 시험판이 깔린 폰에 정식판을 설치하려면 **시험판을 먼저 삭제**해야 합니다(도장이 달라서). 반대도 같습니다.
참여자는 처음부터 정식판만 받으니 영향이 없습니다.

## 다음 정식판을 만들 때 (Claude가 함)
```
cd todak-app && npx cap copy android && cd android && ./gradlew assembleRelease -PslimAbi=arm
```
`android/keystore.properties`가 키 위치·비밀번호를 가리키고 있어 자동으로 서명됩니다.

---

## 2026-09-14 빌드 (현재 배포 후보)
- **`토닥_v0.9_정식서명판_260914.apk`** (33.5MB, arm64+arm32) — 참여자 배포는 이 파일로 하세요.
  - 서명 지문 확인됨: `B9:1F:30:80:81:4B:AD:FB:...:53:9F` — 기존 정식 키와 동일(덮어 설치 가능)
  - 앱 아이콘을 N1(연분홍 바탕 + 입체 새싹)으로 교체
  - 9/9~9/10 변경분 포함: 92 길찾기 지도 선택 팝업, 25-terms 로그인 없이 열람, 아이폰 알림·사진 인식
- 폴더에는 이 APK 한 개만 둡니다. (9/14 작업 중 생긴 중복본 2개는 교수님 확인 후 삭제함)

### 빌드 방법 (자바 주의)
```
set JAVA_HOME=C:\Users\rudtn\.gradle\jdks\eclipse_adoptium-21-amd64-windows.2
cd C:\Users\rudtn\todak-app && npx cap copy android && cd android && gradlew assembleRelease -PslimAbi=arm
```
- **JDK 21 을 써야 합니다.** `.jdks\openjdk-26` 은 안드로이드 빌드 도구(AGP 8.13)가 아직 지원하지 않아 실패합니다.
- `Program Files\Android\Android Studio\jbr` 의 자바는 파일이 빠져 있어 못 씁니다(멀쩡한 쪽은 `Android Studio1\jbr`).
