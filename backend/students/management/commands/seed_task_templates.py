"""Seed the journey TaskTemplates (phases 1–6).

Idempotent: keyed on (phase, order), safe to re-run after edits. Content is
also editable in Django admin — this is the baseline, not the only source.

Offsets are days relative to the anchor (negative = before).
"""

from django.core.management.base import BaseCommand

from students.models import TaskTemplate

A = TaskTemplate.Anchor

# (phase, order, title, why_it_matters, anchor, offset_days, is_critical)
TEMPLATES = [
    # ── Phase 1 — University discovery (anchor: application deadline) ──
    (1, 1, "Explore your matched universities",
     "Your matches are ranked by real fit to your grades, budget and test score — start with the top ones.",
     A.APPLICATION_DEADLINE, -60, False),
    (1, 2, "Compare cities and cost of living",
     "Helsinki rent can be double Oulu's. Where you live changes your budget as much as tuition does.",
     A.APPLICATION_DEADLINE, -50, False),
    (1, 3, "Shortlist 3–5 programs",
     "Applying to 3–5 programs maximises your admission chances without spreading your effort too thin.",
     A.APPLICATION_DEADLINE, -40, True),
    (1, 4, "Check entry requirements for each shortlisted program",
     "Every program has its own GPA, document and language requirements — one missed requirement wastes an application.",
     A.APPLICATION_DEADLINE, -35, False),
    (1, 5, "Research scholarships (EDUFI, Finland Scholarship, university grants)",
     "Many Finnish universities give 50–100% tuition waivers to strong international applicants — but only if you apply for them.",
     A.APPLICATION_DEADLINE, -30, False),

    # ── Phase 2 — Application preparation (anchor: application deadline) ──
    (2, 1, "Book your IELTS/TOEFL test (if not taken)",
     "Test dates fill up and results take ~2 weeks. Without a valid score your application cannot be submitted.",
     A.APPLICATION_DEADLINE, -90, True),
    (2, 2, "Collect transcripts and certificates",
     "Universities need your complete academic history. Getting copies from your school/board takes longer than you think.",
     A.APPLICATION_DEADLINE, -45, False),
    (2, 3, "Get documents attested and translated if needed",
     "Documents not in English need certified translation — unattested documents are a common rejection reason.",
     A.APPLICATION_DEADLINE, -40, False),
    (2, 4, "Write your motivation letter",
     "Admissions tutors read hundreds of letters. A specific, personal letter is the difference between offers and rejections.",
     A.APPLICATION_DEADLINE, -30, False),
    (2, 5, "Build your CV in the Finnish/European format",
     "Finnish academic CVs follow the Europass style — using the local format signals you did your homework.",
     A.APPLICATION_DEADLINE, -25, False),
    (2, 6, "Create your Studyinfo.fi account",
     "Studyinfo.fi is Finland's official application portal — every application goes through it.",
     A.APPLICATION_DEADLINE, -21, False),
    (2, 7, "Fill in your application on Studyinfo",
     "Do this early, not on deadline day — the portal slows down near deadlines and errors need time to fix.",
     A.APPLICATION_DEADLINE, -14, True),
    (2, 8, "Upload all required documents",
     "An application without its attachments is treated as incomplete and won't be assessed.",
     A.APPLICATION_DEADLINE, -10, False),
    (2, 9, "Submit your application",
     "The deadline is absolute: Finnish universities do not accept late applications for any reason.",
     A.APPLICATION_DEADLINE, -7, True),
    (2, 10, "Save the submission confirmation email",
     "Your proof of on-time submission if anything is ever disputed.",
     A.APPLICATION_DEADLINE, -6, False),

    # ── Phase 3 — Offer & confirmation (anchor: offer confirmation deadline) ──
    (3, 1, "Compare your offers side by side",
     "Tuition, city costs, program reputation and job prospects differ — choose with your head, not just the brand name.",
     A.OFFER_DEADLINE, -30, False),
    (3, 2, "Confirm your study place",
     "Missing the confirmation deadline CANCELS your offer automatically. This is the single most important click of the journey.",
     A.OFFER_DEADLINE, -21, True),
    (3, 3, "Get the tuition invoice and bank details",
     "You need the exact IBAN, BIC and amount from your university before you can pay.",
     A.OFFER_DEADLINE, -18, False),
    (3, 4, "Double-check the payment reference number",
     "The #1 costly mistake: a wrong reference number means the university cannot trace your payment for weeks.",
     A.OFFER_DEADLINE, -15, True),
    (3, 5, "Make the international bank transfer",
     "Transfers from Pakistani banks (HBL, UBL, MCB, Meezan) take 5–7 business days — pay well before the deadline.",
     A.OFFER_DEADLINE, -14, True),
    (3, 6, "Save the payment confirmation receipt",
     "Migri requires proof of paid tuition for your residence permit — this receipt is a visa document.",
     A.OFFER_DEADLINE, -7, True),

    # ── Phase 4 — Residence permit / Migri (anchor: visa submission) ──
    (4, 1, "Check your passport has 15+ months validity",
     "Migri requires validity beyond your whole first study year. Renewing a passport in Pakistan takes weeks — check NOW.",
     A.VISA_SUBMISSION, -30, True),
    (4, 2, "Arrange your financial proof (bank statements)",
     "You must show the Migri-required amount (currently ~€560/month — verify the current figure) in an acceptable account.",
     A.VISA_SUBMISSION, -25, True),
    (4, 3, "Buy health insurance meeting Migri requirements",
     "Insurance must be valid from your arrival date with sufficient coverage — applications without it are rejected.",
     A.VISA_SUBMISSION, -15, True),
    (4, 4, "Get passport photos to Migri specification (36×47mm, white background)",
     "Wrong photo specs are a silly but real reason applications get returned.",
     A.VISA_SUBMISSION, -14, False),
    (4, 5, "Gather proof of accommodation",
     "A university housing confirmation or rental contract strengthens your application.",
     A.VISA_SUBMISSION, -10, False),
    (4, 6, "Create your Enter Finland account",
     "Enter Finland is Migri's online portal — the entire permit application happens there.",
     A.VISA_SUBMISSION, -7, False),
    (4, 7, "Submit your residence permit application",
     "Processing takes 8–12 weeks — every day you delay submission delays your decision.",
     A.VISA_SUBMISSION, 0, True),
    (4, 8, "Book your embassy/VFS biometrics appointment",
     "Your application only starts processing after you prove your identity in person — book Islamabad (or Karachi) immediately.",
     A.VISA_SUBMISSION, 7, True),
    (4, 9, "Attend your biometrics appointment",
     "Bring originals of every document. Dress neatly, answer simply and honestly.",
     A.VISA_SUBMISSION, 14, True),
    (4, 10, "Track your application on Enter Finland",
     "Respond to any request for additional documents within days, not weeks — delays reset your place in the queue.",
     A.VISA_SUBMISSION, 30, False),

    # ── Phase 5 — Pre-departure (anchor: arrival) ──
    (5, 1, "Apply for student housing (HOAS/TYS/PSOAS by city)",
     "Student housing is far cheaper than private rentals and queues are long — apply the moment you confirm your place.",
     A.ARRIVAL, -75, True),
    (5, 2, "Book your flight",
     "Booking 6+ weeks ahead saves serious money. Arrive a few days before orientation.",
     A.ARRIVAL, -45, False),
    (5, 3, "Open a Wise account",
     "You'll need to move money before your Finnish bank account exists — Wise bridges that gap cheaply.",
     A.ARRIVAL, -30, False),
    (5, 4, "Notify your bank you're travelling",
     "Pakistani cards get blocked for 'suspicious' foreign transactions unless the bank knows you're moving.",
     A.ARRIVAL, -14, False),
    (5, 5, "Pack for Finland (winter coat, thermals, waterproof boots)",
     "September is mild but winter hits fast. Skip bedding and kitchen items — cheaper at IKEA than in your luggage.",
     A.ARRIVAL, -14, False),
    (5, 6, "Print every document and carry them in hand luggage",
     "Border control can ask for your permit card, acceptance letter and financial proof — phones die, paper doesn't.",
     A.ARRIVAL, -7, True),
    (5, 7, "Download offline maps and plan the airport-to-home route",
     "You'll land tired. Knowing exactly which train/bus to take removes the worst arrival stress.",
     A.ARRIVAL, -3, False),
    (5, 8, "Get €300–500 in cash for your first week",
     "Card activation hiccups happen; cash covers food and transport until everything works.",
     A.ARRIVAL, -2, False),

    # ── Phase 6 — Arrival & first month (anchor: intake start) ──
    (6, 1, "Register at the university and collect your student ID",
     "Your student ID unlocks meal discounts (€2.95 lunches!), transport discounts and the student union.",
     A.INTAKE_START, 2, True),
    (6, 2, "Get a Finnish SIM card (DNA, Elisa or Telia)",
     "A Finnish number is needed for almost every registration that follows.",
     A.INTAKE_START, 3, False),
    (6, 3, "Register with DVV (Digital and Population Data Services)",
     "THE step most students miss. Your Finnish personal identity code (henkilötunnus) is required for banking, healthcare and tax.",
     A.INTAKE_START, 8, True),
    (6, 4, "Complete Migri residence permit registration if requested",
     "Some permits require registering your presence within 3 months of arrival — check your decision letter.",
     A.INTAKE_START, 10, False),
    (6, 5, "Register with Kela for student benefits",
     "Kela handles housing allowance and healthcare access — money you're entitled to but must claim.",
     A.INTAKE_START, 16, False),
    (6, 6, "Open a Finnish bank account (S-Pankki is most newcomer-friendly)",
     "You need the DVV identity code first — that's why this comes after DVV, not before.",
     A.INTAKE_START, 18, True),
    (6, 7, "Join your student union",
     "Union membership unlocks the student card, healthcare (YTHS) and hundreds of discounts.",
     A.INTAKE_START, 20, False),
    (6, 8, "Register with YTHS student healthcare",
     "YTHS gives you doctors, dental and mental-health services for a small annual fee.",
     A.INTAKE_START, 24, False),
    (6, 9, "Get a tax number if you plan to work part-time",
     "You can work up to 30h/week on a student permit — but only with a veronumero. (Verify the current hour limit.)",
     A.INTAKE_START, 26, False),
    (6, 10, "Learn your first 10 Finnish phrases",
     "Finns appreciate even a 'kiitos' — small effort, big goodwill with neighbours and shopkeepers.",
     A.INTAKE_START, 28, False),
]


class Command(BaseCommand):
    help = "Seed (or update) the journey task templates"

    def handle(self, *args, **options):
        created = updated = 0
        for phase, order, title, why, anchor, offset, critical in TEMPLATES:
            _, was_created = TaskTemplate.objects.update_or_create(
                phase=phase,
                order=order,
                defaults={
                    "title": title,
                    "why_it_matters": why,
                    "offset_anchor": anchor,
                    "offset_days": offset,
                    "is_critical": critical,
                    "is_active": True,
                },
            )
            created += was_created
            updated += not was_created
        self.stdout.write(self.style.SUCCESS(f"Templates: {created} created, {updated} updated."))
