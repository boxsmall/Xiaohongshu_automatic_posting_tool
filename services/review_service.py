from services.export_service import mark_payload_approved, update_payload_status


def approve_output(output_dir: str) -> dict:
    return mark_payload_approved(output_dir)


def reject_output(output_dir: str) -> dict:
    return update_payload_status(output_dir, "rejected")

