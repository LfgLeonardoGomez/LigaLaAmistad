"""Regression: unresolved tied positions must allow opening the manual selector.

Requires Vite on localhost:5175. Every API request is intercepted and sent to
the real backend on private SQLite memory; the persistent local demo is untouched.
"""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlsplit

os.environ.update({
    "DATABASE_URL": "sqlite:///:memory:", "CORS_ORIGINS": "http://testserver",
    "COOKIE_SECURE": "false", "COOKIE_SAMESITE": "lax",
    "LIGA_ENV_FILE": str(Path(tempfile.gettempdir()) / "liga-test-no-inherited-settings.env"),
})
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playwright.sync_api import expect, sync_playwright
from tests.americano_fixtures import BASE, americano_api
from tests.test_americano_qualification_api import _finish, _generated, _preview


def run():
    with contextmanager(americano_api.__wrapped__)() as api, sync_playwright() as playwright:
        event = _finish(api, _generated(api, sizes=(4,), stage="final"), tiers=[1, 1, 0, 0])
        preview = _preview(api, event)
        assert [slot["position"] for slot in preview["slots"] if slot["requires_resolution"]] == [1, 2]
        assert len(preview["missing_slots"]) == 2 and not preview["can_confirm"]
        first, second = [str(pair["id"]) for pair in event["registrations"][:2]]
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 960})
        page.set_default_timeout(15000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        writes = []

        def dispatch(route):
            request = route.request
            url = urlsplit(request.url)
            if url.hostname == "localhost" and url.port == 5175:
                return route.continue_()
            if url.hostname == "localhost" and url.port in (8000, 8010):
                headers = {"Access-Control-Allow-Origin": "http://localhost:5175",
                           "Access-Control-Allow-Credentials": "true",
                           "Access-Control-Allow-Headers": "Content-Type,X-Requested-With"}
                if request.method == "OPTIONS":
                    return route.fulfill(status=204, headers=headers)
                response = api.client.request(request.method, url.path + (f"?{url.query}" if url.query else ""),
                                              json=request.post_data_json if request.post_data else None)
                if request.method not in ("GET", "HEAD"):
                    writes.append((url.path, response.status_code))
                return route.fulfill(status=response.status_code, body=response.content,
                                     content_type="application/json", headers=headers)
            route.abort()

        page.route("**/*", dispatch)
        page.goto(f"http://localhost:5175/admin/americanos/{event['id']}/clasificados")
        page.wait_for_load_state("networkidle")
        expect(page.get_by_role("heading", name="Hay puestos empatados por resolver")).to_be_visible()
        expect(page.get_by_role("button", name="Resolver empates", exact=True)).to_be_enabled()
        # Original failure: this button was disabled because missing_slots != [].
        page.get_by_role("button", name="Iniciar playoffs", exact=True).click()
        dialog = page.get_by_role("dialog", name="Resolver empates", exact=True)
        expect(dialog).to_be_visible()
        dialog.get_by_role("button", name="Volver", exact=True).click()
        page.get_by_role("button", name="Resolver empates", exact=True).click()
        expect(dialog.get_by_role("button", name="Guardar desempates")).to_be_disabled()
        dialog.get_by_role("combobox", name="Zona A · plaza 1", exact=True).select_option(second)
        expect(dialog.get_by_role("combobox", name="Zona A · plaza 2").locator(f'option[value="{second}"]')).to_have_attribute("disabled", "")
        expect(dialog.get_by_role("button", name="Guardar desempates")).to_be_disabled()
        dialog.get_by_role("combobox", name="Zona A · plaza 2", exact=True).select_option(first)
        expect(dialog.get_by_role("button", name="Iniciar playoffs", exact=True)).to_be_disabled()
        dialog.get_by_role("button", name="Guardar desempates").click()
        expect(dialog.get_by_role("button", name="Iniciar playoffs", exact=True)).to_be_enabled()
        stored = api.client.get(f"{BASE}/{event['id']}/qualification").json()
        assert stored["can_confirm"] and stored["missing_slots"] == []
        assert [str(slot["registration_id"]) for slot in stored["slots"]] == [second, first]
        dialog.get_by_role("button", name="Volver", exact=True).click()
        rows = page.get_by_role("region", name="Clasificación zona A").get_by_role("row")
        expect(rows.nth(1).get_by_role("cell").first).to_have_text("1")
        expect(rows.nth(1)).to_contain_text("Jugador 1 / Pareja 1")
        expect(rows.nth(2).get_by_role("cell").first).to_have_text("2")
        page.reload()
        page.wait_for_load_state("networkidle")
        page.get_by_role("button", name="Revisar desempates", exact=True).click()
        expect(dialog.get_by_role("combobox", name="Zona A · plaza 1")).to_have_value(second)
        expect(dialog.get_by_role("combobox", name="Zona A · plaza 2")).to_have_value(first)
        page.set_viewport_size({"width": 390, "height": 844})
        screenshot = Path(tempfile.gettempdir()) / "americano-ties-mobile.png"
        page.screenshot(path=str(screenshot), full_page=True)
        dialog.get_by_role("button", name="Iniciar playoffs", exact=True).click()
        expect(page.get_by_role("heading", name="Playoffs", exact=True)).to_be_visible()
        playoffs = api.client.get(f"{BASE}/{event['id']}/playoffs").json()
        assert str(playoffs["nodes"][0]["registration_a"]["id"]) == second
        assert str(playoffs["nodes"][0]["registration_b"]["id"]) == first
        assert len(writes) == 2 and all(status == 200 for _, status in writes), writes
        assert not errors, errors
        browser.close()
        print(json.dumps({"result": "PASS", "case": "real tied positions 1/2", "writes": writes, "screenshot": str(screenshot)}))


if __name__ == "__main__":
    run()
