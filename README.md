# MyBatis 문서 빌드

Bun 환경에서 `bun install --frozen-lockfile`로 의존성을 설치합니다.

- `bun run dev`: `docs/mybatis-guide.md`의 로컬 미리보기
- `bun run build`: 독립 실행 가능한 `dist/index.html` 생성
- `bun run lint`: 구현 소스와 설정을 Oxlint로 검사
- `bun run format` / `bun run format:check`: Oxfmt로 구현 소스와 설정 포맷 또는 확인

생성한 HTML을 단독으로 복사해 브라우저에서 열 수 있습니다.
