"""
Test querying ADCE from hud_support.
"""

try:
    from caster_user_content.util.adce_bridge import adce
    print("ADCE imported successfully!")
    print("Connected:", adce.is_connected())
    print("Zone:", adce.get_current_zone())
    print("Process:", adce.get_current_process())
    print("File:", adce.get_active_file())
except Exception as ex:
    print("ADCE import/query error:", ex)
