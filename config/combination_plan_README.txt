combination_plan.csv

Columns:
- combo_id: ID của tổ hợp sinh dữ liệu.
- attack_type: jailbreak / prompt_injection / benign.
- scenario: scenario chính theo taxonomy.
- mechanism: cơ chế multi-turn chính.
- evasion: kỹ thuật né detection chính hoặc none.
- label: không vi phạm / gây tranh cãi / vi phạm.
- n_samples: số sample dự kiến sinh cho combo. Tổng hiện tại = 5000.
- language: ngôn ngữ chính, mặc định vi.
- priority: high / medium.
- group: nhóm logic dùng để thống kê.
- pair_group: ID nhóm paired safe/unsafe nếu combo thuộc một cặp đối chứng.
- notes: ghi chú ngắn để hướng dẫn prompt sinh dữ liệu.

Gợi ý dùng:
1. Sinh pilot trước bằng cách lấy 5-10 sample mỗi combo high priority.
2. Validate/audit pilot.
3. Sau khi prompt sinh ổn mới sinh đủ n_samples.
