---
name: "\U0001F41B Bug"
about: 버그 수정
title: ''
labels: bug
assignees: ''

---

- type: textarea
    attributes:
      label: 🐛 버그 설명
      description: 어떤 문제가 발생했는지 작성해 주세요.
      placeholder: 발생한 버그를 자세히 설명해 주세요.
    validations:
      required: true

  - type: textarea
    attributes:
      label: 🔁 재현 방법
      description: 버그를 재현하는 단계를 작성해 주세요.
      placeholder: |
        1. ...
        2. ...
        3. ...
    validations:
      required: true

  - type: textarea
    attributes:
      label: ✅ 기대한 동작
      description: 원래 기대했던 동작을 작성해 주세요.
      placeholder: 정상적으로는 어떻게 동작해야 하나요?
    validations:
      required: true

  - type: textarea
    attributes:
      label: ✅ 작업할 내용
      description: 수정할 내용을 체크박스 형태로 작성해 주세요.
      placeholder: |
        - [ ] 원인 파악
        - [ ] 버그 수정
        - [ ] 테스트 작성
    validations:
      required: true

  - type: textarea
    attributes:
      label: 🙋🏻 참고 자료
      description: 참고 자료가 있다면 작성해 주세요.
