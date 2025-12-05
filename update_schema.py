import gspread

def update_comic_inventory_schema(spreadsheet_id, sheet_name):
    """
    Updates the Google Sheet with the comic inventory schema.

    Args:
        spreadsheet_id: The ID of the Google Sheet.
        sheet_name: The name of the sheet to update.
    """

    gc = gspread.service_account(filename='/Users/james/git/pattern/james_agents/james-agents/comic-agent/Comic_Cataloger_Colab_Test.ipynb')
    sh = gc.open_by_key(spreadsheet_id)
    worksheet = sh.worksheet(sheet_name)

    schema = [
        "Series_Title",
        "Series_Short",
        "Issue_Number",
        "Publisher",
        "Year",
        "Auto_Grade_Guess",
        "Condition_Confidence",
        "Detected_Defects",
        "Grading_Notes",
        "Needs_Manual_Check",
        "Estimated_Value"
    ]

    # Update the sheet with the schema
    worksheet.update_row(1, schema)

    print(f"Successfully updated schema in sheet '{sheet_name}' of spreadsheet '{spreadsheet_id}'")

# Example usage (replace with your actual spreadsheet ID and sheet name)
spreadsheet_id = "YOUR_SPREADSHEET_ID"
sheet_name = "Comic Inventory"

update_comic_inventory_schema(spreadsheet_id, sheet_name)