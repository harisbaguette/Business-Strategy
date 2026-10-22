@AGENTS.md
<!-- project-map:start -->
이 프로젝트의 진행 기록은 .project-map/state.json이다.
`node "$HOME/.local/share/project-map/cli.cjs" context --since 마지막revision --root .`로 변경·사용자 답·다음 작업과 실행 후보를 한 번에 확인한다. 처음이면 --since를 뺀다. 필요한 작업만 `read --kind tasks --id ID`(여러 개는 `--id a,b`, ID·제목 조각은 `--match 글자`)로 읽는다. 반영할 때 revision은 `apply --revision current`에 맡긴다.
같은 세션에서 `execution.running`·`execution.ready`를 보고 선행 입력·수정 파일·출력·환경이 충돌하지 않는 도구 실행을 겹친다. 정상 실행 중은 doing으로 유지하고 결과가 필요 없는 일을 계속한다. 지도 편집은 최신 revision에 순서대로 반영한다.
작업 중 새 요구·구현 사실·검증 결과를 반영한다. 다음 행동을 바꾸는 변경은 바로, 나머지는 의미 있는 작업 단위가 끝날 때 `apply --brief`로 기록한다. 반환 현황과 유효한 결과를 재사용하고 사용자 변경·기존 ID·유효한 완료를 보존한다.
산출물·담당·실제 필요한 자료·완료 조건을 작업에 남긴다. 선행 대기는 dependsOn, 실제 막힘은 blockedBy에 원인·해소 조건·다음 행동을 적는다. 실행 검사를 등록한 작업은 `verify --id ID --brief`로 확인한다. 완료·인계 때 실제 결과와 남은 일을 대조한다.
분할·기록 방법이 필요하면 Codex는 ~/.agents/skills/kh-skill-project-start/task-planning.md, Claude Code는 ~/.claude/skills/kh-skill-project-start/task-planning.md, Kilo는 ~/.config/kilo/skills/kh-skill-project-start/task-planning.md를 참고한다. 명령·스키마는 help에 있다.
지도는 현재 요청의 범위를 넓히거나 의무 검토·완료 검사를 추가하지 않는다. HTML은 자동 생성된다.
<!-- project-map:end -->
