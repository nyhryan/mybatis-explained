# PR 02 MyBatis 문서의 정적 HTML 빌드

[PR 01 설명 원고 정리](./mybatis-web-pr-01-content.md)의 편집 원고를 입력으로 사용한다. [PR 03 읽기 화면과 기기 검증](./mybatis-web-pr-03-reading.md)은 이 PR의 빌드 결과를 사용한다.

## 달성 목표

Vite로 `docs/mybatis-guide.md`를 빌드해 독립 실행 가능한 `dist/index.html`을 만든다. 이 파일 하나를 기기에 옮겨 오프라인으로 열어도 본문, Tailwind 스타일, Shiki 코드 색상, 목차와 필요한 그림이 표시돼야 한다.

구현 기본안은 클라이언트 프레임워크 없이 빌드 시 HTML을 생성하는 방식이다. 프레임워크가 필요하다고 판단하면 선택 이유와 단일 파일 검증 결과를 PR에 기록한다. 브라우저의 로컬 파일에서 모듈을 불러오는 과정에 제약이 있으므로 읽기와 목차 이동은 HTML과 CSS만으로 동작하게 한다. [Vite HTML 변환 훅](https://vite.dev/guide/api-plugin.html#transformindexhtml), [MDN JavaScript 모듈](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules#other_differences_between_modules_and_classic_scripts)

## 태스크

각 태스크의 완료 조건을 확인한 항목부터 `[x]`로 바꾸고, 필요한 검증 근거를 PR에 남긴다. 모든 태스크 완료 조건을 체크한 뒤 최종 완료 조건을 별도로 점검하고 체크한다.

### MYB-02-01 빌드와 린트 명령 구성

- [ ] 기존 Bun 환경에서 의존성과 잠금 파일을 준비하고, `bun run dev`와 `bun run build`로 같은 원고를 미리 보고 빌드할 수 있다.
- [ ] Tailwind를 Vite에 연결했다. 원고에서 생성하는 HTML에 필요한 스타일이 프로덕션 산출물에 포함된다. [Tailwind CSS와 Vite](https://tailwindcss.com/docs/installation/using-vite)
- [ ] `bun run lint`는 Oxlint, `bun run format`과 `bun run format:check`는 Oxfmt로 실행한다. 문서 사이트의 구현 소스와 설정이 검사 범위에 포함되고, 빌드 산출물과 대화 원문은 포맷 명령의 범위에서 제외된다. [Oxlint 시작하기](https://oxc.rs/docs/guide/usage/linter/quickstart), [Oxfmt 시작하기](https://oxc.rs/docs/guide/usage/formatter/quickstart)

### MYB-02-02 Markdown과 코드 블록을 빌드 시 렌더링

- [ ] 제목, 표, 목록, 본문과 인라인 코드를 의미에 맞는 HTML로 출력한다. 제목마다 고유 앵커를 생성하고 목차 링크가 해당 절을 가리킨다.
- [ ] Java, XML, SQL 블록은 Shiki로 빌드 시 강조하고, 일반 텍스트 블록은 여백과 줄을 보존해 출력한다. XML 태그, `&lt;`, `#{}`와 `${}`가 원고에 적힌 코드 그대로 보이며, 복사한 코드의 들여쓰기가 유지된다. [Shiki 가이드](https://shiki.style/guide/)
- [ ] PR 01에서 채택한 Mermaid가 있으면 빌드 중 SVG로 렌더링해 HTML에 포함하고 설명을 함께 노출한다. Mermaid 블록이 없다면 그 단계 없이 문서가 빌드된다. [Mermaid CLI](https://mermaid.js.org/config/mermaidCLI.html)

### MYB-02-03 단일 HTML 파일로 내보내기

- [ ] `dist/index.html`에 본문과 컴파일된 CSS가 포함된다. 읽기, 코드 강조, 목차 이동, 채택한 그림 출력은 서버, CDN, 별도 파일 요청 없이 동작한다.
- [ ] `dist/index.html`만 별도 폴더에 옮긴 뒤 네트워크를 끄고 데스크톱 브라우저에서 파일을 직접 열었다. 스타일이 적용되고 목차가 이동하며 Java·XML·SQL 블록이 강조되어 표시된다. 기기 검증 전에 이 결과를 PR에 기록했다.

## 최종 완료 조건

- [ ] 깨끗한 체크아웃에서 `bun install --frozen-lockfile`, `bun run lint`, `bun run format:check`, `bun run build`를 실행했고 모두 성공했다.
- [ ] 복사한 HTML 단독으로 원고 처음부터 마지막 절까지 읽을 수 있고, 목차·예제·채택한 그림이 표시된다.
- [ ] PR 03에서 재현할 수 있도록 실행 명령, 산출물 경로와 로컬 파일 확인 결과를 PR에 기록했다.
