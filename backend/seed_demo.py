"""Seed the database with the hardcoded FTG demo simulation + sample operators.
Usage: python seed_demo.py
"""
from database import init_db, SessionLocal
from models.db_models import Simulation, Operator, TrainingAssignment
from link_utils import generate_link_token

# The hardcoded FTG manifest (matches frontend/src/manifest.ts)
DEMO_MANIFEST = {
    "workflow_id": "ftg_revamped_flow_v1",
    "workflow_name": "FTG - Dimension & Weight Capture",
    "target_users": ["fc_operators"],
    "language": "en",
    "steps": [
        {
            "step_id": 1, "screen": "packaging_options",
            "screenshot": "/screens/ftg_11.png",
            "title": "Choose Packaging Type",
            "instruction": "Tap 'Ships In Own Box' to select packaging",
            "tip": "SIOB means the product ships in its original box without repackaging",
            "expected_action": "TAP",
            "on_wrong_action": "That's not right. Please tap 'Ships In Own Box'.",
            "tap_target": {"x": 3, "y": 35, "width": 94, "height": 12},
        },
        {
            "step_id": 2, "screen": "packaging_options",
            "screenshot": "/screens/ftg_11.png",
            "title": "Proceed to Next Step",
            "instruction": "Tap 'Next' to continue",
            "tip": None,
            "expected_action": "TAP",
            "on_wrong_action": "Tap the Next button at the bottom.",
            "tap_target": {"x": 4, "y": 90, "width": 92, "height": 6},
        },
        {
            "step_id": 3, "screen": "product_identifiers",
            "screenshot": "/screens/ftg_06.png",
            "title": "Select Product Category",
            "instruction": "Tap the dropdown to select a category",
            "tip": "Product category is mandatory when SDP config is enabled for your FC",
            "expected_action": "TAP",
            "on_wrong_action": "Please tap the Product Category dropdown.",
            "tap_target": {"x": 4, "y": 35, "width": 92, "height": 6},
        },
        {
            "step_id": 4, "screen": "product_identifiers",
            "screenshot": "/screens/ftg_06.png",
            "title": "Continue to Dimensions",
            "instruction": "Tap 'Next' to proceed",
            "tip": "Scannable ID and Image URL are optional fields",
            "expected_action": "TAP",
            "on_wrong_action": "Tap the Next button at the bottom.",
            "tap_target": {"x": 4, "y": 90, "width": 92, "height": 6},
        },
    ],
    "quiz_breaks": [
        {
            "after_step": 2,
            "questions": [
                {
                    "question": "What does SIOCB stand for?",
                    "options": [
                        "Ships In Own Box",
                        "Ships In Own Case Box",
                        "Ships In Original Container Box",
                        "Standard Item Own Case Box",
                    ],
                    "correct": 1,
                },
            ],
        },
    ],
}

DEMO_ASSESSMENT = {
    "questions": [
        {"question": "What does SIOCB stand for?", "options": ["Ships In Own Box", "Ships In Own Case Box", "Ships In Original Container Box", "Standard Item Own Case Box"], "correct": 1},
        {"question": "What is the minimum items per box for SIOCB?", "options": ["1", "2", "5", "10"], "correct": 1},
        {"question": "Which field is mandatory on the Product Identifiers screen?", "options": ["Scannable ID", "Product Category", "Image URL", "None"], "correct": 1},
        {"question": "What happens if V-Measure dimensions exceed machine limits?", "options": ["Data saves anyway", "Error shown, must use manual", "App crashes", "Auto-retry"], "correct": 1},
        {"question": "Who can use Manual mode for dimension entry?", "options": ["Anyone", "Only HRMS-tagged users", "Only managers", "Only admins"], "correct": 1},
    ],
    "pass_threshold": 0.6,
}

SAMPLE_OPERATORS = [
    ("EMP001", "Rahul Kumar"),
    ("EMP002", "Priya Singh"),
    ("EMP003", "Amit Sharma"),
    ("EMP004", "Neha Gupta"),
    ("EMP005", "Vikram Patel"),
]


def seed():
    init_db()
    db = SessionLocal()

    # Check if already seeded
    existing = db.query(Simulation).filter(Simulation.workflow_id == "ftg_revamped_flow_v1").first()
    if existing:
        print("⚠️  Demo data already exists. Skipping seed.")
        db.close()
        return

    # Create simulation
    sim = Simulation(
        workflow_id="ftg_revamped_flow_v1",
        workflow_name="FTG - Dimension & Weight Capture",
        manifest_json=DEMO_MANIFEST,
        assessment_json=DEMO_ASSESSMENT,
        status="published",
    )
    db.add(sim)
    db.flush()
    print(f"✅ Created simulation: {sim.workflow_name} (id: {sim.id})")

    # Create operators and assign
    for emp_id, name in SAMPLE_OPERATORS:
        op = Operator(operator_id=emp_id, name=name)
        db.add(op)
        db.flush()

        token = generate_link_token(sim.id, op.id)
        assignment = TrainingAssignment(
            simulation_id=sim.id,
            operator_id=op.id,
            link_token=token,
        )
        db.add(assignment)
        db.flush()
        print(f"  📋 Assigned to {name} ({emp_id}) → /t/{token}")

    db.commit()
    db.close()
    print("\n✅ Seed complete! Start the backend and try the admin panel.")


if __name__ == "__main__":
    seed()
