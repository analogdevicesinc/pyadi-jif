"""Debug test for Clock Configurator selectbox."""

import pytest


@pytest.mark.e2e
def test_debug_clock_selectbox(clock_page):
    """Debug the Clock Configurator selectbox interaction."""
    page = clock_page.page

    # Print the current page content
    print("\n=== Page Title ===")
    print(page.title())

    # Find the "Select a part" label
    print("\n=== Looking for 'Select a part' label ===")
    label = page.locator('label:has-text("Select a part")')
    print(f"Found label: {label.count()} elements")

    if label.count() > 0:
        print(f"Label visible: {label.first.is_visible()}")
        print(f"Label text: {label.first.text_content()}")

        # Find the combobox
        print("\n=== Looking for combobox ===")
        selectbox_container = label.first.locator("..")
        combobox = selectbox_container.locator('[role="combobox"]')
        print(f"Found combobox: {combobox.count()} elements")

        if combobox.count() > 0:
            print(f"Combobox visible: {combobox.first.is_visible()}")
            print(f"Combobox text: {combobox.first.text_content()!r}")
            aria_expanded = combobox.first.get_attribute("aria-expanded")
            print(f"Combobox aria-expanded: {aria_expanded}")

            # Click it
            print("\n=== Clicking combobox ===")
            combobox.first.click()

            # Wait for options to appear or aria-expanded to change
            print("Waiting for options to appear...")
            page.wait_for_function(
                "() => document.querySelector('[role=\"option\"]') !== null"
                " || document.querySelector('"
                '[role="combobox"][aria-expanded="true"]\') !== null',
                timeout=5000,
            )

            # Look for options
            print("\n=== Looking for options ===")
            options = page.locator('[role="option"]')
            print(f"Found options: {options.count()} elements")

            if options.count() > 0:
                for i in range(min(5, options.count())):
                    text = options.nth(i).text_content()
                    print(f"Option {i}: {text}")
            else:
                print("No options found!")
                expanded = combobox.first.get_attribute("aria-expanded")
                print(f"Combobox aria-expanded after click: {expanded}")

                # Look for any element with hmc7044
                elems = page.locator("text=/hmc7044/i")
                print(f"Elements with 'hmc7044': {elems.count()}")

                # Check for listbox
                listbox = page.locator('[role="listbox"]')
                print(f"Found listbox: {listbox.count()} elements")

                # Check all roles
                all_with_role = page.locator("[role]")
                print(f"Total elements with role attribute: {all_with_role.count()}")
