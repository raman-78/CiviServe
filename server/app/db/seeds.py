"""Reference-catalog + scheme seeds for dev/tests bootstrap.

Production data lands through the seeds in ``database/seeds`` executed via
Alembic; this module only guarantees a working minimal catalog locally so that
FKs and defaults resolve before real ingestion exists.
"""

# ruff: noqa: E501  (long bilingual seed content lines)

from __future__ import annotations

from datetime import UTC, datetime

from app.models.document import DocumentType
from app.models.reference import Language, State
from app.models.scheme import Scheme
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

_BASE_LANGUAGES = [
    ("en", "English", "English", "Latin", False, True, True, True),
    ("hi", "Hindi", "हिन्दी", "Devanagari", False, True, True, True),
    ("bn", "Bengali", "বাংলা", "Bengali", False, True, True, True),
    ("ta", "Tamil", "தமிழ்", "Tamil", False, True, True, True),
    ("te", "Telugu", "తెలుగు", "Telugu", False, True, True, True),
    ("kn", "Kannada", "ಕನ್ನಡ", "Kannada", False, True, True, True),
    ("ml", "Malayalam", "മലയാളം", "Malayalam", False, True, True, True),
    ("gu", "Gujarati", "ગુજરાતી", "Gujarati", False, True, True, True),
    ("mr", "Marathi", "मराठी", "Devanagari", False, True, True, True),
    ("pa", "Punjabi", "ਪੰਜਾਬੀ", "Gurmukhi", False, True, True, True),
    ("or", "Odia", "ଓଡ଼ିଆ", "Odia", False, True, True, True),
    ("as", "Assamese", "অসমীয়া", "Bengali", False, True, True, True),
    ("ur", "Urdu", "اردو", "Perso-Arabic", True, True, True, False),
]

_STATES = [
    ("AP", "Andhra Pradesh", "ఆంధ్ర ప్రదేశ్", "south", False),
    ("KA", "Karnataka", "ಕರ್ನಾಟಕ", "south", False),
    ("TN", "Tamil Nadu", "தமிழ்நாடு", "south", False),
    ("UP", "Uttar Pradesh", "उत्तर प्रदेश", "north", False),
    ("WB", "West Bengal", "পশ্চিমবঙ্গ", "east", False),
    ("MH", "Maharashtra", "महाराष्ट्र", "west", False),
]


async def seed_reference_data(session: AsyncSession) -> None:
    """Idempotently insert base languages and states."""
    existing_langs = {code for (code,) in (await session.execute(select(Language.code))).all()}
    to_add = [row for row in _BASE_LANGUAGES if row[0] not in existing_langs]
    session.add_all(
        Language(
            code=code,
            name=name,
            native_name=native,
            script=script,
            is_rtl=rtl,
            stt=stt,
            tts=tts,
            indic_trans=indic,
            is_fallback=(code == "en"),
        )
        for code, name, native, script, rtl, stt, tts, indic in to_add
    )

    existing_state = {c for (c,) in (await session.execute(select(State.code))).all()}
    session.add_all(
        State(code=code, name=name, name_native=native, region=region, is_ut=is_ut)
        for code, name, native, region, is_ut in _STATES
        if code not in existing_state
    )
    await session.commit()


# ---------------------------------------------------------------------------
# Scheme seeds — a small, realistic catalog so search/filters/bookmarks work
# locally before real ingestion. Idempotent upsert by `code`.
# ---------------------------------------------------------------------------


def _loc(en: str, native: str = "") -> dict:
    return {"en": en, "native": native}


def _rule(field: str, operator: str, value: object, description: str, **extra: object) -> dict:
    rule = {"field": field, "operator": operator, "value": value, "description": description}
    rule.update(extra)
    return rule


def _doc(name: str, kind: str, *, ocr: bool = False, optional: bool = False) -> dict:
    from uuid import uuid4

    return {
        "id": str(uuid4()),
        "name": name,
        "kind": kind,
        "localizedNames": {"en": name.replace("_", " ").title()},
        "optional": optional,
        "ocrSupported": ocr,
    }


def _step(step: int, title: str, description: str | None = None, mode: str = "online") -> dict:
    return {
        "step": step,
        "title": _loc(title),
        "description": _loc(description) if description else None,
        "mode": mode,
    }


def _faq(question: str, answer: str) -> dict:
    from uuid import uuid4

    return {"id": str(uuid4()), "question": _loc(question), "answer": _loc(answer)}


def _scheme(
    code: str,
    name: tuple[str, str],
    summary: tuple[str, str],
    description: tuple[str, str],
    category: str,
    ministry: str,
    **kw: object,
) -> Scheme:
    base: dict[str, object] = {
        "code": code,
        "name_en": name[0],
        "name_native": name[1],
        "summary_en": summary[0],
        "summary_native": summary[1],
        "description_en": description[0],
        "description_native": description[1],
        "category": category,
        "ministry": ministry,
        "scope": "central",
        "state_code": "*",
        "applicable_states": [],
        "target_beneficiaries": [],
        "benefits": [],
        "eligibility_rules": [],
        "required_documents": [],
        "application_steps": [],
        "faqs": [],
        "keywords": [],
        "tags": [],
        "application_links": {},
        "scheme_status": "published",
        "popularity": 0,
        "view_count": 0,
        "last_verified_at": datetime(2026, 3, 1, tzinfo=UTC),
    }
    base.update(kw)
    return Scheme(**base)  # type: ignore[arg-type]


_SCHEMES: list[Scheme] = [
    _scheme(
        "PM-KISAN",
        ("PM Kisan Samman Nidhi", "पीएम किसान सम्मान निधि"),
        (
            "Income support of ₹6,000 per year for landholding farmer families.",
            "भूमि-धारक किसान परिवारों के लिए प्रति वर्ष ₹6,000 की आय सहायता।",
        ),
        (
            "PM-KISAN provides direct income support of ₹6,000 per year to all landholding farmer families in India, paid in three equal instalments of ₹2,000 directly to the Aadhaar-seeded bank accounts. The scheme aims to supplement the financial needs of farmers for procurement of inputs like seeds, fertilisers and other needs.",
            "पीएम-किसान योजना भारत की सभी भूमि-धारक किसान परिवारों को प्रति वर्ष ₹6,000 की प्रत्यक्ष आय सहायता प्रदान करती है, जिसे ₹2,000 की तीन समान किस्तों में आधार-सीडेड बैंक खाते में सीधे भेजा जाता है।",
        ),
        "agriculture",
        "Ministry of Agriculture & Farmers Welfare",
        sub_category="income-support",
        department="Department of Agriculture & Farmers Welfare",
        target_beneficiaries=["Landholding farmer families"],
        benefits=[
            "₹6,000/year in three instalments of ₹2,000",
            "Direct transfer to Aadhaar-seeded bank account",
        ],
        eligibility_rules=[
            _rule("occupation", "in", ["farmer"], "Must be a landholding farmer family."),
            _rule("is_farmer", "eq", True, "Applicable to farmers."),
        ],
        required_documents=[
            _doc("AADHAAR", "identity", ocr=True),
            _doc("LAND_RECORD", "land"),
        ],
        application_steps=[
            _step(1, "Visit pmkisan.gov.in and go to 'Farmers Corner'"),
            _step(2, "Enter Aadhaar number and select 'Data Correction' to verify details"),
            _step(3, "Benefit is auto-credited to the seeded bank account", mode="both"),
        ],
        application_links={
            "online": "https://pmkisan.gov.in",
            "offline": "Visit your nearest CSC or PM-Kisan Mitra.",
            "helpline": "155261",
            "sourceUrl": "https://pmkisan.gov.in",
        },
        official_website="https://pmkisan.gov.in",
        official_application_link="https://pmkisan.gov.in",
        faqs=[
            _faq(
                "Who is eligible for PM-KISAN?",
                "Landholding farmer families, except income-tax payers and certain government employees.",
            ),
            _faq(
                "How do I check my payment status?",
                "On pmkisan.gov.in, 'Farmers Corner' → 'Beneficiary Status' using Aadhaar.",
            ),
        ],
        keywords=["kisan", "crop", "farmer income", "rupee 6000"],
        tags=["farmers", "KCC", "income support", "land"],
        popularity=98,
        view_count=12450,
        last_verified_at=datetime(2026, 2, 20, tzinfo=UTC),
    ),
    _scheme(
        "PM-JAY",
        ("Ayushman Bharat PM-JAY", "आयुष्मान भारत प्रधानमंत्री जन आरोग्य योजना"),
        (
            "Health insurance cover of ₹5 lakh per family per year for hospitalisation.",
            "परिवार के लिए प्रति वर्ष 5 लाख रुपये तक का स्वास्थ्य बीमा कवर।",
        ),
        (
            "Ayushman Bharat Pradhan Mantri Jan Arogya Yojana provides a health cover of up to ₹5 lakh per family per year for secondary and tertiary hospitalisation. It is one of the world's largest health assurance schemes, providing cashless and paperless access to empanelled hospitals for eligible families.",
            "आयुष्मान भारत प्रधानमंत्री जन आरोग्य योजना प्रति परिवार प्रति वर्ष 5 लाख रुपये तक का स्वास्थ्य कवर प्रदान करती है। यह दुनिया की सबसे बड़ी स्वास्थ्य आश्वासन योजनाओं में से एक है।",
        ),
        "health",
        "Ministry of Health & Family Welfare",
        department="National Health Authority",
        target_beneficiaries=["SECC 2011 beneficiary families", "Ration-card holding families"],
        benefits=["₹5 lakh health cover", "Cashless treatment", "Coverage for 1,900+ procedures"],
        eligibility_rules=[
            _rule(
                "income_band",
                "in",
                ["below-poverty", "low"],
                "Beneficiary families per SECC 2011 database.",
            ),
        ],
        required_documents=[_doc("AADHAAR", "identity", ocr=True), _doc("RATION_CARD", "identity")],
        application_steps=[
            _step(1, "Check your name in the PM-JAY beneficiary list"),
            _step(2, "Visit an empanelled hospital with Aadhaar"),
            _step(3, "Get cashless treatment at the hospital", mode="offline"),
        ],
        application_links={
            "online": "https://beneficiary.nha.gov.in",
            "offline": "Visit the nearest empanelled hospital or CSC.",
            "helpline": "14555",
        },
        official_website="https://pmjay.gov.in",
        official_application_link="https://beneficiary.nha.gov.in",
        faqs=[
            _faq(
                "How do I check eligibility?",
                "Search your name in the beneficiary list on the NHA portal using ration card or mobile number.",
            ),
            _faq(
                "Is the scheme cashless?",
                "Yes, treatment is cashless and paperless at empanelled hospitals.",
            ),
        ],
        keywords=["insurance", "hospital", "treatment", "health card"],
        tags=["health", "insurance", "hospital", "SES"],
        popularity=95,
        view_count=11000,
    ),
    _scheme(
        "PM-AWAS",
        ("PM Awas Yojana (Gramin)", "प्रधानमंत्री आवास योजना (ग्रामीण)"),
        (
            "Assistance to build a pucca house with basic amenities for the homeless.",
            "बेघर परिवारों के लिए पक्का आवास निर्माण सहायता।",
        ),
        (
            "PM Awas Yojana Gramin (PMAY-G) aims to provide a pucca house with basic amenities to all houseless households and households living in kutcha houses. Beneficiaries get financial assistance for house construction and the house is geotagged and verified.",
            "प्रधानमंत्री आवास योजना ग्रामीण का उद्देश्य सभी बेघर परिवारों और कच्चे मकानों में रहने वाले परिवारों को बुनियादी सुविधाओं के साथ पक्का आवास उपलब्ध कराना है।",
        ),
        "housing",
        "Ministry of Rural Development",
        department="Department of Rural Development",
        target_beneficiaries=["Houseless households", "Households in kutcha houses"],
        benefits=[
            "Financial assistance for house construction",
            "Basic amenities (toilet, LPG, electricity)",
        ],
        eligibility_rules=[
            _rule(
                "income_band",
                "in",
                ["below-poverty", "low"],
                "Households without a pucca house per SECC 2011.",
            ),
        ],
        required_documents=[
            _doc("AADHAAR", "identity", ocr=True),
            _doc("BANK_PASSBOOK", "bank", ocr=True),
        ],
        application_steps=[
            _step(1, "Apply through the local Gram Panchayat", mode="offline"),
            _step(2, "Verification of house status and eligibility"),
            _step(3, "Funds transferred in instalments on completion stages"),
        ],
        application_links={
            "online": "https://pmayg.nic.in",
            "offline": "Apply through Gram Panchayat.",
            "helpline": "1800-11-6446",
        },
        official_website="https://pmayg.nic.in",
        official_application_link="https://pmayg.nic.in",
        faqs=[_faq("Can a family apply twice?", "No, one pucca house per eligible family.")],
        keywords=["housing", "house", "construction", "pradhan mantri awaas"],
        tags=["housing", "poor", "gramin"],
        popularity=80,
        view_count=8400,
    ),
    _scheme(
        "PM-SHREYAS",
        ("PM SHREYAS Scholarships", "पीएम श्रेयस छात्रवृत्ति"),
        (
            "Scholarships for OBC, EBC and minority students in higher education.",
            "ओबीसी, ईबीसी और अल्पसंख्यक छात्रों के लिए उच्च शिक्षा छात्रवृत्ति।",
        ),
        (
            "PM SHREYAS provides central sector scholarships to OBC, EBC and minority community students for higher education. It covers tuition fees and maintenance allowances for post-matric courses through the National Scholarship Portal.",
            "पीएम श्रेयस ओबीसी, ईबीसी और अल्पसंख्यक समुदाय के छात्रों को उच्च शिक्षा के लिए केंद्रीय क्षेत्र की छात्रवृत्ति प्रदान करता है।",
        ),
        "education",
        "Ministry of Education",
        department="Department of Higher Education",
        sub_category="scholarship",
        target_beneficiaries=["OBC, EBC and minority students", "Post-matric students"],
        benefits=["Tuition fee reimbursement", "Maintenance allowance"],
        eligibility_rules=[
            _rule("income_band", "lte", 250000, "Family income up to ₹2.5 lakh/year."),
            _rule("is_student", "eq", True, "Must be a student."),
        ],
        required_documents=[
            _doc("CASTE_CERTIFICATE", "caste"),
            _doc("INCOME_CERTIFICATE", "income"),
        ],
        application_steps=[
            _step(1, "Register on the National Scholarship Portal"),
            _step(2, "Fill the application and upload documents"),
            _step(3, "Institute verification, then disbursement"),
        ],
        application_links={"online": "https://scholarships.gov.in", "helpline": "0120-6619540"},
        official_website="https://scholarships.gov.in",
        official_application_link="https://scholarships.gov.in",
        faqs=[
            _faq(
                "What is the income limit?",
                "Family income up to ₹2.5 lakh per annum for OBC/EWS; ₹2.5 lakh for minority schemes.",
            )
        ],
        keywords=["scholarship", "student", "obc", "minority", "education loan"],
        tags=["students", "OBC", "EBC", "minority"],
        popularity=76,
        view_count=6300,
    ),
    _scheme(
        "TN-BC-EDU",
        ("Tamil Nadu Backward Classes Scholarship", "தமிழ்நாடு பிற்படுத்தப்பட்ட வகுப்பினர் உதவித்தொகை"),
        (
            "Post-matric scholarship for students from backward classes in Tamil Nadu.",
            "தமிழ்நாட்டில் பிற்படுத்தப்பட்ட வகுப்பினரைச் சேர்ந்த மாணவர்களுக்கான கல்வி உதவித்தொகை.",
        ),
        (
            "The Tamil Nadu Backward Classes Department offers a post-matric scholarship covering fee reimbursement and a monthly maintenance allowance for students belonging to Backward Classes, Most Backward Classes and Denotified Communities studying in Tamil Nadu.",
            "தமிழ்நாட்டில் பிற்படுத்தப்பட்ட, மிகவும் பிற்படுத்தப்பட்ட மற்றும் பறைமறுத்த வகுப்பினரைச் சேர்ந்த மாணவர்களுக்கு கல்வி உதவித்தொகை வழங்கப்படுகிறது.",
        ),
        "education",
        "Government of Tamil Nadu",
        sub_category="scholarship",
        scope="state",
        state_code="TN",
        applicable_states=["TN"],
        department="Backward Classes, Most Backward Classes & Minorities Welfare Dept.",
        target_beneficiaries=["BC/MBC/DNC students in TN"],
        benefits=["Fee reimbursement", "Monthly maintenance allowance"],
        eligibility_rules=[
            _rule("state", "eq", "TN", "Resident of Tamil Nadu."),
            _rule("is_student", "eq", True, "Must be a student."),
        ],
        required_documents=[
            _doc("AADHAAR", "identity", ocr=True),
            _doc("BONAFIDE", "identity", optional=True),
        ],
        application_steps=[
            _step(1, "Apply through the Head of Institution", mode="offline"),
            _step(2, "Verify caste certificate and income"),
            _step(3, "Disbursement to the college account"),
        ],
        application_links={
            "online": "https://bcmbcm.tn.gov.in",
            "offline": "Through college/school head of institution.",
        },
        official_website="https://bcmbcm.tn.gov.in",
        faqs=[
            _faq(
                "Who should apply?",
                "Students of BC/MBC/DNC communities enrolled in post-matric courses in Tamil Nadu.",
            )
        ],
        keywords=["tamil nadu", "scholarship", "backward classes", "post matric"],
        tags=["students", "BC", "Tamil Nadu"],
        popularity=45,
        view_count=3900,
    ),
    _scheme(
        "PM-VISHWAKARMA",
        ("PM Vishwakarma Yojana", "पीएम विश्वकर्मा योजना"),
        (
            "Support for artisans and craftspeople with skill training and credit.",
            "शिल्पकारों और कारीगरों के लिए कौशल प्रशिक्षण और ऋण सहायता।",
        ),
        (
            "PM Vishwakarma provides artisans and craftspeople engaged in 18 traditional trades with recognition, skill upgradation, toolkits, and collateral-free credit support of up to ₹3 lakh. It aims to strengthen the informal economy of artisans.",
            "पीएम विश्वकर्मा योजना 18 पारंपरिक व्यवसायों के शिल्पकारों को मान्यता, कौशल उन्नयन, टूलकिट और 3 लाख रुपये तक का ऋण सहायता प्रदान करती है।",
        ),
        "employment",
        "Ministry of Micro, Small and Medium Enterprises",
        department="Office of Development Commissioner (MSME)",
        target_beneficiaries=["Artisans and craftspeople"],
        benefits=[
            "Collateral-free credit up to ₹3 lakh",
            "Skill upgradation training",
            "Stipend during training",
        ],
        eligibility_rules=[
            _rule("is_self_employed", "eq", True, "Must be self-employed in a listed trade."),
            _rule("age", "between", [18, 60], "Age between 18 and 60 years."),
        ],
        required_documents=[_doc("AADHAAR", "identity", ocr=True)],
        application_steps=[
            _step(1, "Register on pmvishwakarma.gov.in"),
            _step(2, "Choose your trade and complete basic training"),
            _step(3, "Get toolkits and access collateral-free credit"),
        ],
        application_links={"online": "https://pmvishwakarma.gov.in", "helpline": "1800-267-1012"},
        official_website="https://pmvishwakarma.gov.in",
        official_application_link="https://pmvishwakarma.gov.in",
        faqs=[
            _faq(
                "How many trades are covered?",
                "18 traditional trades including carpenter, blacksmith, potter, tailor and barber.",
            )
        ],
        keywords=["artisan", "craftsman", "skill", "toolkit", "self employed"],
        tags=["artisans", "MSME", "self-employed"],
        popularity=70,
        view_count=5200,
    ),
    _scheme(
        "IGNOAPS",
        ("Indira Gandhi National Old Age Pension", "इंदिरा गांधी राष्ट्रीय वृद्धावस्था पेंशन योजना"),
        (
            "Monthly pension for senior citizens below the poverty line.",
            "गरीबी रेखा से नीचे के वरिष्ठ नागरिकों के लिए मासिक पेंशन।",
        ),
        (
            "IGNOAPS provides a monthly pension to persons aged 60 years and above who belong to households below the poverty line. The central share is supplemented by the states, and benefits are disbursed through DBT.",
            "इंदिरा गांधी राष्ट्रीय वृद्धावस्था पेंशन योजना 60 वर्ष और उससे अधिक आयु के गरीबी रेखा से नीचे के व्यक्तियों को मासिक पेंशन प्रदान करती है।",
        ),
        "pension",
        "Ministry of Rural Development",
        department="Department of Rural Development",
        target_beneficiaries=["Senior citizens above BPL"],
        benefits=["Monthly pension ₹200–₹500 (varies by state)"],
        eligibility_rules=[
            _rule("age", "gte", 60, "Age 60 years or above."),
            _rule("income_band", "eq", "below-poverty", "Below poverty line household."),
            _rule("is_senior_citizen", "eq", True, "Senior citizen."),
        ],
        required_documents=[
            _doc("AADHAAR", "identity", ocr=True),
            _doc("BPL_CERTIFICATE", "income"),
        ],
        application_steps=[
            _step(1, "Apply at the nearest Gram Panchayat / CSC", mode="offline"),
            _step(2, "Verify age and BPL status"),
            _step(3, "Monthly pension credited via DBT"),
        ],
        application_links={
            "offline": "Apply through Gram Panchayat or block office.",
            "helpline": "1800-11-5656",
        },
        faqs=[
            _faq(
                "At what age is the pension available?",
                "60 years for the general category; the enhanced rate applies from age 80.",
            )
        ],
        keywords=["pension", "old age", "senior citizen", "bpl"],
        tags=["pension", "senior-citizen", "BPL"],
        popularity=72,
        view_count=4800,
    ),
    _scheme(
        "PMGKAY",
        ("Pradhan Mantri Garib Kalyan Anna Yojana", "प्रधानमंत्री गरीब कल्याण अन्न योजना"),
        (
            "Free foodgrains to NFSA households under the Garib Kalyan package.",
            "गरीब कल्याण पैकेज के तहत एनएफएसए परिवारों को मुफ्त खाद्यान्न।",
        ),
        (
            "PMGKAY supplies free foodgrains (5 kg per person per month) to households covered under the National Food Security Act. It is a key welfare intervention ensuring food security for the poorest households.",
            "पीएम-जीकेएवाई राष्ट्रीय खाद्य सुरक्षा अधिनियम के तहत पात्र परिवारों को प्रति व्यक्ति प्रति माह 5 किलो मुफ्त खाद्यान्न उपलब्ध कराती है।",
        ),
        "food-security",
        "Ministry of Consumer Affairs, Food & Public Distribution",
        department="Department of Food & Public Distribution",
        target_beneficiaries=["NFSA households (AAY + priority)"],
        benefits=["5 kg free foodgrains per person per month"],
        eligibility_rules=[
            _rule("income_band", "in", ["below-poverty", "low"], "Households covered under NFSA."),
        ],
        required_documents=[_doc("RATION_CARD", "identity")],
        application_steps=[
            _step(1, "Confirm your ration card is NFSA-linked"),
            _step(2, "Collect foodgrains from the fair price shop", mode="offline"),
        ],
        application_links={"helpline": "1800-267-1515"},
        faqs=[
            _faq(
                "Who receives this scheme?",
                "Households listed under AAY and priority categories of the NFSA ration list.",
            )
        ],
        keywords=["food", "ration", "grains", "garib kalyan"],
        tags=["food-security", "ration", "NFSA"],
        popularity=68,
        view_count=4400,
    ),
    _scheme(
        "PM-MUDRA",
        ("PM Mudra Yojana", "पीएम मुद्रा योजना"),
        (
            "Collateral-free loans up to ₹10 lakh for micro enterprises.",
            "सूक्ष्म उद्यमों के लिए 10 लाख रुपये तक का बिना संपत्ति-गिरवी ऋण।",
        ),
        (
            "Pradhan Mantri MUDRA Yojana offers collateral-free loans up to ₹10 lakh to small and micro enterprises under the Shishu, Kishore and Tarun categories. A large share of beneficiaries are women entrepreneurs.",
            "प्रधानमंत्री मुद्रा योजना शिशु, किशोर और तरुण श्रेणियों के तहत सूक्ष्म उद्यमों को 10 लाख रुपये तक का बिना गिरवी ऋण प्रदान करती है।",
        ),
        "financial-inclusion",
        "Ministry of Finance",
        department="Department of Financial Services",
        target_beneficiaries=["Micro/small business owners", "Women entrepreneurs"],
        benefits=["Loans up to ₹10 lakh", "Three categories: Shishu, Kishore, Tarun"],
        eligibility_rules=[
            _rule("is_self_employed", "eq", True, "Must be running a micro enterprise."),
            _rule(
                "is_women",
                "eq",
                True,
                "Women-owned enterprises encouraged.",
                is_required=False,
            ),
        ],
        required_documents=[_doc("AADHAAR", "identity", ocr=True), _doc("BANK_ACCOUNT", "bank")],
        application_steps=[
            _step(1, "Visit your bank / CSC and ask for MUDRA loan", mode="offline"),
            _step(2, "Submit business plan and KYC"),
            _step(3, "Loan sanctioned under Shishu/Kishore/Tarun"),
        ],
        application_links={"helpline": "1800-180-1116"},
        faqs=[
            _faq(
                "How much loan can I get?",
                "Up to ₹50,000 (Shishu), ₹5 lakh (Kishore) and ₹10 lakh (Tarun).",
            )
        ],
        keywords=["loan", "business", "mudra", "micro enterprise", "women"],
        tags=["loan", "business", "women", "financial"],
        popularity=74,
        view_count=5000,
    ),
    _scheme(
        "SUGAMYA-BHARAT",
        ("Sugamya Bharat Abhiyan", "सुगम्य भारत अभियान"),
        (
            "Accessibility for persons with disabilities across public spaces.",
            "सार्वजनिक स्थानों पर दिव्यांगजनों के लिए सुगम्यता।",
        ),
        (
            "Sugamya Bharat Abhiyan (Accessible India Campaign) is a nationwide drive to achieve universal accessibility for persons with disabilities in the built environment, transport and ICT. It focuses on creating barrier-free public spaces and accessible websites.",
            "सुगम्य भारत अभियान दिव्यांगजनों के लिए निर्मित पर्यावरण, परिवहन और आईसीटी में सार्वभौमिक सुगम्यता प्राप्त करने के लिए राष्ट्रव्यापी अभियान है।",
        ),
        "disability",
        "Ministry of Social Justice & Empowerment",
        department="Department of Empowerment of Persons with Disabilities",
        target_beneficiaries=["Persons with disabilities"],
        benefits=["Barrier-free public infrastructure", "Accessible transport and ICT"],
        eligibility_rules=[
            _rule("is_disabled", "eq", True, "For persons with disabilities."),
        ],
        required_documents=[_doc("DISABILITY_CERTIFICATE", "disability")],
        application_steps=[
            _step(1, "Locate accessibility audits in your city"),
            _step(2, "Report an inaccessible facility via the campaign portal"),
        ],
        application_links={"online": "https://accessibleindia.gov.in", "helpline": "011-2436-2767"},
        official_website="https://accessibleindia.gov.in",
        faqs=[
            _faq(
                "Who can report accessibility issues?",
                "Any person can report barriers at public facilities through the campaign portal.",
            )
        ],
        keywords=["disability", "accessibility", "divyangjan", "barrier free"],
        tags=["disability", "accessibility"],
        popularity=42,
        view_count=2100,
    ),
    _scheme(
        "KA-RAITHA",
        ("Karnataka Raitha Sanmana", "ಕರ್ನಾಟಕ ರೈತ ಸನ್ಮಾನ"),
        ("Income support for farmers in Karnataka.", "ಕರ್ನಾಟಕದ ರೈತರಿಗೆ ಆದಾಯ ಬೆಂಬಲ.ಕಾರ್ನ್"),
        (
            "Karnataka Raitha Sanmana provides direct income support to farmers in Karnataka. Eligible landholding farmers receive financial assistance through the state government's Krishi Bhagya initiative.",
            "ಕರ್ನಾಟಕ ರೈತ ಸನ್ಮಾನ ಯೋಜನೆ ರಾಜ್ಯದ ರೈತರಿಗೆ ನೇರ ಆದಾಯ ಬೆಂಬಲವನ್ನು ಒದಗಿಸುತ್ತದೆ.",
        ),
        "agriculture",
        "Government of Karnataka",
        scope="state",
        state_code="KA",
        applicable_states=["KA"],
        department="Department of Agriculture",
        target_beneficiaries=["Landholding farmers in Karnataka"],
        benefits=["Annual income support for farmers"],
        eligibility_rules=[
            _rule("state", "eq", "KA", "Resident of Karnataka."),
            _rule("is_farmer", "eq", True, "Must be a farmer."),
        ],
        required_documents=[_doc("AADHAAR", "identity", ocr=True)],
        application_steps=[
            _step(1, "Apply through the Krishi Bhagya portal"),
            _step(2, "Verify land records and bank details"),
            _step(3, "Benefit credited via DBT"),
        ],
        application_links={"online": "https://krishi.karnataka.gov.in"},
        official_website="https://krishi.karnataka.gov.in",
        faqs=[
            _faq(
                "How do I update my bank details?",
                "Through the Krishi Bhagya portal with OTP verification.",
            )
        ],
        keywords=["karnataka", "farmer", "income support"],
        tags=["farmers", "Karnataka", "state-scheme"],
        popularity=50,
        view_count=3100,
    ),
]


async def seed_schemes(session: AsyncSession) -> None:
    """Idempotently upsert the seed scheme catalog by `code`."""
    stored = {scheme.code: scheme for scheme in (await session.execute(select(Scheme))).scalars()}
    columns = [col.name for col in Scheme.__table__.columns if col.name != "id"]
    for seed in _SCHEMES:
        row = stored.get(seed.code)
        if row is None:
            session.add(seed)
        else:
            for column in columns:
                setattr(row, column, getattr(seed, column))
    await session.commit()


# ---------------------------------------------------------------------------
# Document-catalog seeds (Prompt 11). Mirrors `DocumentCode` + `DocumentKind`
# in shared/src/domain/document.ts; single source of truth for the accepted
# file formats and OCR support flags served to clients.
# ---------------------------------------------------------------------------

#: (code, kind, name_en, ocr_supported, accepted_formats, guidance)
_DOCUMENT_TYPES: list[tuple] = [
    (
        "AADHAAR",
        "identity",
        "Aadhaar Card",
        True,
        ["pdf", "jpg", "jpeg", "png"],
        {
            "summaryEn": "Your 12-digit Aadhaar number. Upload a clear photo of the card or the My Aadhaar PDF.",
            "officialSourceUrl": "https://uidai.gov.in",
        },
    ),
    (
        "PAN_CARD",
        "identity",
        "PAN Card",
        True,
        ["pdf", "jpg", "jpeg", "png"],
        {
            "summaryEn": "Permanent Account Number card issued by the Income Tax Department.",
            "officialSourceUrl": "https://www.incometax.gov.in",
        },
    ),
    (
        "RATION_CARD",
        "identity",
        "Ration Card",
        True,
        ["jpg", "jpeg", "png"],
        {
            "summaryEn": "Family ration card issued by the state's Civil Supplies department.",
        },
    ),
    (
        "BANK_PASSBOOK",
        "bank",
        "Bank Passbook",
        True,
        ["jpg", "jpeg", "png"],
        {
            "summaryEn": "First page of your bank passbook showing account holder and IFSC.",
        },
    ),
    (
        "BANK_ACCOUNT",
        "bank",
        "Bank Account Proof",
        True,
        ["pdf", "jpg", "jpeg", "png"],
        {
            "summaryEn": "Passbook, bank statement or account-holder certificate.",
        },
    ),
    (
        "INCOME_CERTIFICATE",
        "income",
        "Income Certificate",
        True,
        ["pdf", "jpg", "jpeg", "png"],
        {
            "summaryEn": "Issued by the Tehsildar / local authority. Upload the latest copy.",
        },
    ),
    (
        "COMMUNITY_CERTIFICATE",
        "caste",
        "Community Certificate",
        True,
        ["pdf", "jpg", "jpeg", "png"],
        {
            "summaryEn": "Community/caste certificate issued by the competent authority.",
        },
    ),
    (
        "CASTE_CERTIFICATE",
        "caste",
        "Caste Certificate",
        True,
        ["pdf", "jpg", "jpeg", "png"],
        {
            "summaryEn": "Caste certificate issued by the Revenue department.",
        },
    ),
    (
        "RESIDENCE_CERTIFICATE",
        "address",
        "Residence Certificate",
        True,
        ["pdf", "jpg", "jpeg", "png"],
        {
            "summaryEn": "Proof of residence issued by the local revenue office.",
        },
    ),
    (
        "DISABILITY_CERTIFICATE",
        "disability",
        "Disability Certificate",
        True,
        ["pdf", "jpg", "jpeg", "png"],
        {
            "summaryEn": "Certificate of disability issued by an authorised medical board.",
        },
    ),
    (
        "BIRTH_CERTIFICATE",
        "family",
        "Birth Certificate",
        True,
        ["pdf", "jpg", "jpeg", "png"],
        {"summaryEn": "Registered birth certificate issued by the municipal authority."},
    ),
    (
        "MARK_SHEET",
        "age",
        "Marksheet / Grade Card",
        True,
        ["pdf", "jpg", "jpeg", "png"],
        {"summaryEn": "Latest qualifying examination marksheet or grade card."},
    ),
    (
        "VOTER_ID",
        "identity",
        "Voter ID (EPIC)",
        True,
        ["pdf", "jpg", "jpeg", "png"],
        {"summaryEn": "Voter identification card issued by the Election Commission."},
    ),
    (
        "PASSPORT",
        "identity",
        "Passport",
        True,
        ["pdf", "jpg", "jpeg", "png"],
        {"summaryEn": "Indian passport. Upload the front information page."},
    ),
    (
        "LAND_RECORD",
        "land",
        "Land Record / Patta",
        True,
        ["pdf", "jpg", "jpeg", "png"],
        {
            "summaryEn": "Record of Rights (RoR), patta or mutation extract of the land.",
        },
    ),
    (
        "PHOTOGRAPH",
        "photo",
        "Passport-size Photograph",
        False,
        ["jpg", "jpeg", "png"],
        {"summaryEn": "Recent passport-size photograph with a plain background."},
    ),
    (
        "MARRIAGE_CERTIFICATE",
        "family",
        "Marriage Certificate",
        True,
        ["pdf", "jpg", "jpeg", "png"],
        {"summaryEn": "Registered marriage certificate."},
    ),
    (
        "APPLICATION_FORM",
        "other",
        "Application Form",
        False,
        ["pdf", "jpg", "jpeg", "png"],
        {"summaryEn": "The scheme's prescribed application form, if specifically required."},
    ),
    (
        "OTHER",
        "other",
        "Other Document",
        False,
        ["pdf", "jpg", "jpeg", "png"],
        {"summaryEn": "Any other supporting document requested by the scheme."},
    ),
]


async def seed_document_types(session: AsyncSession) -> None:
    """Idempotently upsert the document-type catalog by code."""
    stored = {t.code: t for t in (await session.execute(select(DocumentType))).scalars()}
    for code, kind, name_en, ocr, formats, guidance in _DOCUMENT_TYPES:
        if code in stored:
            row = stored[code]
            row.kind = kind
            row.name_en = name_en
            row.ocr_supported = ocr
            row.accepted_formats = formats
            row.guidance = guidance
        else:
            session.add(
                DocumentType(
                    code=code,
                    kind=kind,
                    name_en=name_en,
                    localized_names={"en": name_en},
                    ocr_supported=ocr,
                    accepted_formats=formats,
                    guidance=guidance,
                )
            )
    await session.commit()


# ---------------------------------------------------------------------------
# Service-centre catalog seeds (maps/locator prompt). A small, geocoded corpus
# so nearby/manual scans work locally before real ingestion. Mirrors
# ``ServiceCenter`` in shared/src/domain/centers.ts.
# ---------------------------------------------------------------------------

#: (name, centre_type, state_code, district, pincode, lat, lng, services, timings,
#:  phone, source, source_url)
_CENTRES: list[tuple] = [
    (
        "CSC Anna Nagar",
        "csc",
        "TN",
        "Chennai",
        "600040",
        13.0850,
        80.2130,
        ["Aadhaar", "PM-KISAN registration", "e-Governance"],
        "Mon–Sat, 9:00 AM – 6:00 PM",
        "044-26201000",
        "api",
        "https://csc.gov.in",
    ),
    (
        "e-Sevai Kendra T Nagar",
        "esevai",
        "TN",
        "Chennai",
        "600017",
        13.0418,
        80.2341,
        ["Certificates", "Subsidies", "e-Sevai"],
        "Mon–Fri, 9:30 AM – 5:30 PM",
        "044-24341111",
        "api",
        "https://esevai.tn.gov.in",
    ),
    (
        "TN Seva Kendra Anna Nagar",
        "seva-kendra",
        "TN",
        "Chennai",
        "600040",
        13.0878,
        80.2104,
        ["Certificates", "Old-age pension", "Birth/death registration"],
        "Mon–Fri, 10:00 AM – 5:30 PM",
        "044-26200000",
        "manual",
        "https://tnseva.tn.gov.in",
    ),
    (
        "CSC Guindy",
        "csc",
        "TN",
        "Chennai",
        "600032",
        13.0106,
        80.2203,
        ["Aadhaar", "Banking", "Bill payments"],
        "Mon–Sat, 9:30 AM – 6:00 PM",
        "044-22330000",
        "api",
        "https://csc.gov.in",
    ),
    (
        "CSC Jayanagar",
        "csc",
        "KA",
        "Bengaluru",
        "560041",
        12.9250,
        77.5938,
        ["Aadhaar", "PAN application", "Passport"],
        "Mon–Sat, 9:00 AM – 7:00 PM",
        "080-26630000",
        "api",
        "https://csc.gov.in",
    ),
    (
        "Karnataka One Indiranagar",
        "seva-kendra",
        "KA",
        "Bengaluru",
        "560038",
        12.9784,
        77.6408,
        ["Certificates", "Land records", "Caste certificate"],
        "Mon–Fri, 9:30 AM – 5:00 PM",
        "080-25200000",
        "api",
        "https://karnatakaone.gov.in",
    ),
    (
        "CSC Andheri East",
        "csc",
        "MH",
        "Mumbai",
        "400069",
        19.1136,
        72.8697,
        ["Aadhaar", "Education certificates", "Bill payments"],
        "Mon–Sat, 9:00 AM – 6:00 PM",
        "022-26250000",
        "api",
        "https://csc.gov.in",
    ),
    (
        "CSC Punjabi Bagh",
        "csc",
        "DL",
        "West Delhi",
        "110026",
        28.6569,
        77.0947,
        ["Aadhaar", "Banking", "PAN card"],
        "Mon–Sat, 9:00 AM – 6:00 PM",
        "011-25600000",
        "api",
        "https://csc.gov.in",
    ),
]


async def seed_service_centres(session: AsyncSession) -> None:
    """Idempotently upsert the service-centre seed catalog by name+state."""
    from datetime import UTC, datetime
    from uuid import uuid4

    from app.models.center import ServiceCentre

    existing = {
        f"{c.name}|{c.state_code}": c
        for c in (await session.execute(select(ServiceCentre))).scalars()
    }
    for (
        name,
        centre_type,
        state_code,
        district,
        pincode,
        lat,
        lng,
        services,
        timings,
        phone,
        source,
        source_url,
    ) in _CENTRES:
        cell = existing.get(f"{name}|{state_code}")
        if cell is None:
            session.add(
                ServiceCentre(
                    id=uuid4(),
                    name=name,
                    centre_type=centre_type,
                    state_code=state_code,
                    district=district,
                    pincode=pincode,
                    lat=lat,
                    lng=lng,
                    services=list(services),
                    timings=timings,
                    phone=phone,
                    languages=["en"],
                    verified=True,
                    source=source,
                    source_url=source_url,
                    last_verified_at=datetime(2026, 6, 1, tzinfo=UTC),
                    active=True,
                )
            )
        else:
            cell.name = name
            cell.centre_type = centre_type
            cell.state_code = state_code
            cell.district = district
            cell.pincode = pincode
            cell.lat = lat
            cell.lng = lng
            cell.services = list(services)
            cell.timings = timings
            cell.phone = phone
            cell.verified = True
            cell.source = source
            cell.source_url = source_url
    await session.commit()
