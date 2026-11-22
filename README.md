# MyBatis 문서 빌드

Bun 환경에서 의존성을 설치하고 문서를 빌드합니다.

```sh
bun install --frozen-lockfile
bun run build
```

입력은 `docs/mybatis-guide.md`, 결과물은 `dist/index.html`입니다. 결과 HTML에는 본문과 스타일, 코드 강조가 포함되므로 이 파일 하나를 복사해 오프라인으로 열 수 있습니다.

- `bun run dev`: 원고의 로컬 개발 미리보기
- `bun run lint`: 구현 소스와 설정을 Oxlint로 검사
- `bun run format` / `bun run format:check`: Oxfmt로 구현 소스와 설정 포맷 또는 확인

## 열기와 검증

데스크톱에서 `dist/index.html`만 별도 폴더에 복사하고 네트워크를 끈 뒤 브라우저에서 직접 열어 본문, 목차 이동과 코드 강조를 확인합니다. 직접 열기가 제한되는 환경에서는 프로젝트 루트에서 아래 명령을 실행하고 `http://127.0.0.1:8001/`을 열어 화면을 확인할 수 있습니다. 이 로컬 서버 확인은 오프라인 파일 직접 열기 검증을 대신하지 않습니다.

```sh
python -m http.server --bind 127.0.0.1 -d dist/ 8001
```

Android와 iOS에서는 각 기기에 `index.html`만 복사하고 비행기 모드를 켠 뒤 파일 앱 또는 로컬 HTML을 표시할 수 있는 뷰어에서 엽니다. 본문 처음과 마지막, 목차 이동, Java·XML·SQL 강조, 코드와 표의 가로 스크롤을 확인하고 사용한 OS 버전, 앱, 열기 경로를 기록합니다.

단일 HTML을 오프라인으로 열어 본문, 목차 이동과 Java·XML·SQL 코드 강조를 확인했습니다. 확인된 열기 경로는 다음과 같습니다.

- Android: 기기의 로컬 HTML 앱
- iOS 26.7.3: Preview 앱
- 데스크톱: 브라우저에서 로컬 파일 직접 열기

Android와 데스크톱의 OS 버전 및 앱 이름: 미기록.
