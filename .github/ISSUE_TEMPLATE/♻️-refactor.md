---
name: "♻️ Refactor"
about: 코드 리팩토링
title: ''
labels: refactor
assignees: ''

---

- type: textarea
    attributes:
      label: 📄 설명
      description: 리팩토링이 필요한 부분을 작성해 주세요.
      placeholder: 어떤 코드를 개선하려고 하나요?
    validations:
      required: true

  - type: textarea
    attributes:
      label: 🎯 리팩토링 목적
      description: 리팩토링을 하는 이유를 작성해 주세요.
      placeholder: 가독성 개선, 중복 제거, 구조 개선 등
    validations:
      required: true

  - type: textarea
    attributes:
      label: ✅ 작업할 내용
      description: 할 일을 체크박스 형태로 작성해 주세요.
      placeholder: |
        - [ ] 중복 코드 제거
        - [ ] 메서드 분리
        - [ ] 테스트 확인
    validations:
      required: true

  - type: textarea
    attributes:
      label: 🙋🏻 참고 자료
      description: 참고 자료가 있다면 작성해 주세요.
