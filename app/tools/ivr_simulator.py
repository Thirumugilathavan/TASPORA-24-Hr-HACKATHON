"""Interactive Command-Line IVR Simulator for CareBridge Voice Access.

Allows developers and evaluators to experience the full button-phone keypad journey
(Tamil and English) without real telephony provider credentials or physical hardware.

Usage:
    python -m app.tools.ivr_simulator
"""
import asyncio
import os
import sys
from uuid import uuid4

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core.database import AsyncSessionLocal
from app.services.ivr_service import IVRService


def print_banner():
    print("=" * 70)
    print("  CAREBRIDGE VOICE ACCESS — BUTTON PHONE / IVR SIMULATOR")
    print("  'Healthcare access without a smartphone or internet'")
    print("=" * 70)
    print("Simulating keypad phone interaction (DTMF Keypad: 0-9, *, #)\n")


async def run_simulator():
    print_banner()
    default_phone = "9876500001"
    prompt_phone = input(f"Enter caller phone number [{default_phone}]: ").strip()
    caller_phone = prompt_phone if prompt_phone else default_phone
    call_sid = f"sim-{uuid4().hex[:10]}"

    async with AsyncSessionLocal() as db:
        service = IVRService(db)

        # 1. Start Call
        print(f"\n[CALL STARTED] Calling CareBridge IVR from: {caller_phone} (SID: {call_sid})")
        resp = await service.start_call(call_sid=call_sid, caller_phone=caller_phone)

        while True:
            print("\n" + "-" * 70)
            print(f"PHONE SPEAKER [{resp.language.upper()} | Menu: {resp.current_menu} | Auth: {'VERIFIED' if resp.is_verified else 'GUEST'}]:")
            print(f">> \"{resp.speak_text}\"")
            print("-" * 70)

            if resp.hangup or resp.session_status == "COMPLETED":
                print("\n[CALL TERMINATED BY SYSTEM]")
                break

            print("\nKeypad Options: [0-9], [*], [#], or [q] to quit simulator")
            digits = input("Press Keypad Button(s) > ").strip()

            if digits.lower() == "q":
                print("\n[USER HUNG UP CALL]")
                break

            resp = await service.process_dtmf(call_sid=call_sid, digits=digits)


if __name__ == "__main__":
    asyncio.run(run_simulator())
