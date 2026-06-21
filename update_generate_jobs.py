import re
import json

DOMAIN_DESC_VI = {
    "academic_discussion": "Thảo luận học thuật, trao đổi kiến thức hàn lâm",
    "agent_workflow": "Luồng làm việc của AI agent (gọi tool, lập kế hoạch, thực thi)",
    "ai_assistant_config": "Cấu hình, hướng dẫn cài đặt và thiết lập cho AI Assistant",
    "ai_persona": "Định hình tính cách, vai diễn của trợ lý AI",
    "benchmark_eval": "Đánh giá hiệu năng và tính năng mô hình theo các tiêu chuẩn (benchmarks)",
    "calendar_email_agent": "AI quản lý lịch trình và email tự động",
    "career_advice": "Tư vấn hướng nghiệp, phát triển sự nghiệp",
    "chatbot_persona": "Tùy chỉnh tính cách (persona) riêng cho chatbot",
    "chatbot_testing": "Kiểm thử chatbot, tìm lỗi và ranh giới an toàn",
    "coding_assistant": "Trợ lý lập trình, viết code, review code và gỡ lỗi",
    "company_knowledge_base": "Hỏi đáp dựa trên cơ sở tri thức nội bộ của công ty",
    "creative_writing": "Sáng tác văn học, viết truyện, kịch bản, thơ ca",
    "crm_assistant": "Trợ lý hỗ trợ quản lý quan hệ khách hàng (CRM)",
    "customer_support_bot": "Chatbot chăm sóc và hỗ trợ khách hàng",
    "customer_support_tool": "Công cụ hỗ trợ cho nhân viên chăm sóc khách hàng",
    "daily_chat": "Trò chuyện thường ngày, tán gẫu",
    "data_analysis": "Phân tích dữ liệu, xử lý số liệu, xuất biểu đồ",
    "dataset_design": "Thiết kế, xây dựng bộ dữ liệu huấn luyện",
    "dataset_labeling": "Gán nhãn dữ liệu, phân loại văn bản",
    "discussion_forum": "Diễn đàn trao đổi, bình luận cộng đồng",
    "document_processing": "Xử lý, trích xuất thông tin từ tài liệu văn bản",
    "document_qa": "Hỏi đáp nội dung dựa trên tài liệu (RAG)",
    "document_search": "Tìm kiếm thông tin trong tập tài liệu",
    "email_assistant": "Trợ lý viết, tóm tắt và quản lý hộp thư email",
    "email_processing": "Xử lý và phân loại email tự động",
    "fictional_simulation": "Mô phỏng bối cảnh giả tưởng, tình huống giả định",
    "finetuning_discussion": "Thảo luận về kỹ thuật tinh chỉnh (fine-tuning) mô hình",
    "general_chat": "Hỏi đáp kiến thức chung, trò chuyện đa chủ đề",
    "general_knowledge": "Kiến thức bách khoa, thông tin chung",
    "guardrail_eval": "Đánh giá các cơ chế bảo vệ (guardrail) của AI",
    "guardrail_modeling": "Xây dựng và phát triển mô hình kiểm duyệt (guardrail)",
    "homework_help": "Hỗ trợ làm bài tập, giải bài tập",
    "hr_policy_qa": "Hỏi đáp về chính sách nhân sự (HR)",
    "internal_chatbot": "Chatbot nội bộ dành riêng cho nhân viên công ty",
    "internal_search": "Hệ thống tìm kiếm thông tin nội bộ doanh nghiệp",
    "jailbreak_detection": "Phát hiện và phân tích các thủ thuật jailbreak",
    "learning_tutor": "Gia sư AI hỗ trợ học tập, giải thích khái niệm",
    "paper_discussion": "Thảo luận, phân tích các bài báo nghiên cứu khoa học",
    "private_context_assistant": "Trợ lý AI xử lý ngữ cảnh chứa dữ liệu riêng tư, nhạy cảm",
    "prompt_engineering_discussion": "Thảo luận về kỹ thuật viết và tối ưu prompt",
    "prompt_injection_analysis": "Phân tích các lỗ hổng chèn mã độc (prompt injection)",
    "prompt_testing": "Thử nghiệm, kiểm tra độ ổn định của prompt",
    "rag_qa": "Hỏi đáp sử dụng kỹ thuật RAG (Retrieval-Augmented Generation)",
    "retrieved_document": "Xử lý và tổng hợp tài liệu được truy xuất",
    "roleplay_game": "Trò chơi nhập vai (Role-playing game)",
    "safety_eval": "Đánh giá an toàn và rủi ro của AI",
    "safety_research": "Nghiên cứu về tính an toàn của mô hình ngôn ngữ",
    "security_awareness": "Đào tạo và nâng cao nhận thức bảo mật",
    "story_planning": "Lên ý tưởng, dàn ý cho câu chuyện/tiểu thuyết",
    "study_planning": "Lập kế hoạch học tập, lộ trình đào tạo",
    "system_instruction_eval": "Đánh giá mức độ tuân thủ system instruction của AI",
    "task_assistant": "Trợ lý thực hiện và theo dõi các tác vụ",
    "task_instruction": "Cung cấp chỉ dẫn cụ thể để hoàn thành tác vụ",
    "taxonomy_design": "Thiết kế hệ thống phân loại, taxonomy",
    "tool_agent": "AI có khả năng tự động gọi và sử dụng công cụ (tool-using agent)",
    "uploaded_file_analysis": "Phân tích nội dung file do người dùng tải lên",
    "webpage_summarization": "Tóm tắt nội dung trang web",
    "workflow_automation": "Tự động hóa luồng quy trình công việc",
    "writing_help": "Hỗ trợ viết lách, soạn thảo văn bản, sửa lỗi diễn đạt"
}

# Auto-generate English descriptions
DOMAIN_DESC_EN = {}
for k, v in DOMAIN_DESC_VI.items():
    # Simple capitalization for English as a fallback, or we can leave it to format
    DOMAIN_DESC_EN[k] = k.replace('_', ' ').title()

def modify_generate_jobs():
    path = 'src/generate_jobs.py'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Insert the dicts right before LABEL_DEFINITIONS_VI
    if "DOMAIN_DESC_VI" not in content:
        dict_str = "DOMAIN_DESC_VI: dict[str, str] = {\n"
        for k, v in DOMAIN_DESC_VI.items():
            dict_str += f'    "{k}": "{v}",\n'
        dict_str += "}\n\n"
        
        dict_str += "DOMAIN_DESC_EN: dict[str, str] = {\n"
        for k, v in DOMAIN_DESC_EN.items():
            dict_str += f'    "{k}": "{v}",\n'
        dict_str += "}\n\n"
        
        content = content.replace("LABEL_DEFINITIONS_VI = ", dict_str + "LABEL_DEFINITIONS_VI = ")

    # 2. Modify build_prompt
    
    # In language == "vi"
    content = content.replace(
        'Lĩnh vực/Ngữ cảnh (Context domain): {job["domain"]}',
        'Lĩnh vực/Ngữ cảnh (Context domain): {domain_desc} ({job["domain"]})'
    )
    
    # In language == "en"
    content = content.replace(
        'Context domain: {job["domain"]}',
        'Context domain: {domain_desc} ({job["domain"]})'
    )
    
    # Add domain resolution logic at the top of build_prompt
    if "domain_desc =" not in content:
        # We need to insert `domain = job["domain"]` and the dict lookup
        insert_code = """
    domain   = job["domain"]
    if language == "vi":
        domain_desc = DOMAIN_DESC_VI.get(domain, domain.replace('_', ' '))
    else:
        domain_desc = DOMAIN_DESC_EN.get(domain, domain.replace('_', ' '))
"""
        # Find where to insert it, right after `style    = job["style"]`
        content = re.sub(
            r'style\s*=\s*job\["style"\]',
            'style    = job["style"]' + insert_code,
            content
        )

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("Successfully updated generate_jobs.py with Domain Descriptions!")

if __name__ == '__main__':
    modify_generate_jobs()
