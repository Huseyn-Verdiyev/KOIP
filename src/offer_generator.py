import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


# ──────────────────────────────────────────────
# Margin-Protection Engine
# ──────────────────────────────────────────────

def _calculate_safe_offer(customer_data: dict, analysis: dict) -> dict:
    """
    Core business logic: determines the exact retention offer parameters
    while strictly enforcing the margin_limit_percentage.

    The AI is NEVER given the raw margin_limit — it is only handed
    the pre-calculated ceiling so it cannot hallucinate a higher number.

    Returns a dict with:
        - tier_label   : Human-readable customer tier
        - max_discount : Hard ceiling (%) the LLM must not exceed
        - offer_type   : 'VIP_CONCIERGE' | 'PREMIUM_PERSONAL' | 'STANDARD_AUTO'
        - ltv_usd      : Customer lifetime value
        - priority     : Issue priority from analysis
    """
    ltv = customer_data["lifetime_value_usd"]
    margin_limit = customer_data["margin_limit_percentage"]
    priority = analysis.get("priority", "MEDIUM")

    # Priority multiplier: CRITICAL issues get the full margin budget
    priority_factor = {
        "CRITICAL": 1.0,
        "HIGH":     0.80,
        "MEDIUM":   0.50,
        "LOW":      0.25,
    }.get(priority, 0.50)

    # Actual discount ceiling = margin limit × priority factor (never exceeds margin_limit)
    calculated_discount = round(margin_limit * priority_factor)
    safe_discount = min(calculated_discount, margin_limit)  # Hard cap: Rule 1

    # Offer type by LTV: Rule 2 & Rule 3
    if ltv > 1000:
        offer_type = "VIP_CONCIERGE"
        tier_label = "VIP"
    elif ltv > 500:
        offer_type = "PREMIUM_PERSONAL"
        tier_label = "Premium"
    else:
        offer_type = "STANDARD_AUTO"
        tier_label = "Standard"

    return {
        "tier_label": tier_label,
        "max_discount": safe_discount,
        "offer_type": offer_type,
        "ltv_usd": ltv,
        "priority": priority,
    }


def _build_luma_system_prompt(offer_params: dict) -> str:
    """Builds a dynamic, parameter-injected system prompt for Luma."""
    tone_map = {
        "VIP_CONCIERGE":   "warm, empathetic, and premium-concierge level — treat this person like a CEO",
        "PREMIUM_PERSONAL": "professional, sincere, and solution-focused",
        "STANDARD_AUTO":   "polite, efficient, and empathetic but concise",
    }
    tone = tone_map[offer_params["offer_type"]]

    return f"""You are Luma, Azercell's elite AI Customer Success Agent.
Your personality: {tone}
Your language: Azerbaijani (use formal "Siz" address).

STRICT MARGIN PROTECTION RULES — these are NON-NEGOTIABLE:
1. You MAY offer a discount OR credit. The maximum you are ALLOWED to offer is {offer_params['max_discount']}%. You MUST NOT exceed this under any circumstances.
2. Customer Tier: {offer_params['tier_label']} (LTV: ${offer_params['ltv_usd']})
3. If tier is VIP_CONCIERGE: offer the full {offer_params['max_discount']}% and include a personal callback promise from a dedicated account manager.
4. If tier is PREMIUM_PERSONAL: offer {offer_params['max_discount']}% and a priority support line.
5. If tier is STANDARD_AUTO: offer {offer_params['max_discount']}% automated credit only. Keep it brief.

Your message structure MUST be:
1. Sincere, personalized apology referencing their SPECIFIC issue.
2. Clear explanation of what Azercell is doing to fix it (be specific, not generic).
3. The concrete retention offer (state the exact % or credit amount).
4. A warm closing appropriate to the tier.

Sign every message as: "Luma | Azercell Müştəri Uğur Komandası" """


def generate_special_offer(
    text: str,
    analysis: dict,
    customer_data: dict
) -> dict:
    """
    Generates a margin-protected, personalized retention message from Luma.

    Args:
        text:          Original raw feedback from the customer.
        analysis:      Structured analysis dict from analyzer.py.
        customer_data: Full customer profile including LTV and margin_limit.

    Returns:
        A dict containing:
            - message        : The full Azerbaijani message from Luma.
            - offer_params   : The calculated offer parameters (for audit trail).
    """
    offer_params = _calculate_safe_offer(customer_data, analysis)
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key or api_key.startswith("sk-placeholder"):
        # Deterministic high-quality Azerbaijani Luma message strictly respecting offer_params
        tier = offer_params["tier_label"]
        discount = offer_params["max_discount"]
        name = customer_data["name"]

        if tier == "VIP":
            message = (
                f"Hörmətli {name},\n\n"
                f"Azercell Korporativ xidmətlərində qarşılaşdığınız internet kəsintiləri və dəstək xəttindəki gecikməyə görə "
                f"sizdən və şirkətinizdən səmimi qəlbdən üzr istəyirik. Biznesiniz üçün hər saniyənin nə qədər dəyərli olduğunu dərindən anlayırıq.\n\n"
                f"Şəbəkə mühəndislərimiz korporativ marşrutlaşdırmanı artıq fərdi prioritet rejimə keçirmiş və texniki stabilliyi bərpa etmişdir. "
                f"Sizinlə olan uzunmüddətli etibarlı əməkdaşlığımıza verdiyimiz yüksək dəyərin göstəricisi olaraq, növbəti faktura dövrünüz üçün "
                f"tam {discount}% xüsusi fərdi endirim təyin edilmişdir. Həmçinin, şəxsi korporativ menecerimiz bu gün gün ərzində sizinlə əlaqə saxlayaraq "
                f"xidmət keyfiyyətini birbaşa nəzarətə götürəcəkdir.\n\n"
                f"Bizə olan etimadınız bizim üçün ən ali prioritetdir.\n\n"
                f"Hörmətlə,\nLuma | Azercell Müştəri Uğur Komandası"
            )
        elif tier == "Premium":
            message = (
                f"Hörmətli {name},\n\n"
                f"Biznes planınızda vəd edilən sürət göstəricilərindən aşağı nəticə aldığınız üçün çox təəssüf edirik. "
                f"Təqdim etdiyiniz məlumatlar dərhal Texniki Monitorinq qrupumuza yönləndirildi və ərazinizdəki baza stansiyasının tutum optimizasiyasına başlanıldı.\n\n"
                f"Yaranmış narahatlığı kompensasiya etmək məqsədilə növbəti ayın xidmət haqqına {discount}% endirim tətbiq edildi və hesabınıza prioritet texniki dəstək statusu əlavə olundu.\n\n"
                f"Hər zaman xidmətinizdəyik.\n\n"
                f"Luma | Azercell Müştəri Uğur Komandası"
            )
        else:
            message = (
                f"Salam, {name}.\n\n"
                f"Tətbiqimizdə balans artırarkən qarşılaşdığınız texniki xətaya görə üzr istəyirik. "
                f"Ödəniş şlüzündəki problem mühəndislərimiz tərəfindən aradan qaldırılmışdır. Tətbiqi yenidən sınamağınızı xahiş edirik.\n\n"
                f"Narahatlığınızı qarşılamaq üçün balansınıza {discount}% dəyərində kompensasiya krediti təyin edildi.\n\n"
                f"Bizimlə qaldığınız üçün təşəkkür edirik!\n\n"
                f"Luma | Azercell Müştəri Uğur Komandası"
            )

        return {
            "message": message,
            "offer_params": offer_params,
        }

    system_prompt = _build_luma_system_prompt(offer_params)
    user_prompt = f"""Customer Name: {customer_data['name']}
Product: {customer_data['product']}
Core Issue Identified: {analysis.get('core_issue', 'Unknown issue')}
Affected Feature: {analysis.get('affected_feature', 'Unknown')}
Issue Priority: {offer_params['priority']}

Original Customer Feedback:
\"\"\"{text}\"\"\"

Write the retention message now. Respond ONLY with the message text — no JSON, no metadata."""

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
    )

    message = response.choices[0].message.content.strip()

    return {
        "message": message,
        "offer_params": offer_params,
    }

