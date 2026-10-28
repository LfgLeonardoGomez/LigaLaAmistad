"""Browser regression against Vite + the real API on a private in-memory DB.

Run Vite first (no build), then from backend/:
  .venv/Scripts/python.exe browser_checks/americano_courts_wizard.py

All API requests are intercepted and forwarded to the isolated TestClient.
No production database, browser profile, credentials or live API are used.
"""

import json
import os
from contextlib import contextmanager
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import urlsplit

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["CORS_ORIGINS"] = "http://testserver"
os.environ["COOKIE_SECURE"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playwright.sync_api import expect, sync_playwright
from tests.americano_fixtures import BASE, add_registration, americano_api, create_event
from tests.test_americano_confirmation import _confirm
from tests.test_americano_qualification_api import _finish, _preview, _put


def run():
    with contextmanager(americano_api.__wrapped__)() as api, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 960})
        page.set_default_timeout(10000)
        expect.set_options(timeout=10000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        writes = []
        native_dialogs = []
        page.on("dialog", lambda dialog: (native_dialogs.append(dialog.message), dialog.dismiss()))
        lose_next_court_reply = False
        lose_next_fixture_reply = False

        def route_request(route):
            nonlocal lose_next_court_reply, lose_next_fixture_reply
            request = route.request
            url = urlsplit(request.url)
            if url.hostname == "127.0.0.1" and url.port == 5175:
                return route.continue_()
            if url.hostname == "localhost" and url.port in (8000, 8010):
                headers = {"Access-Control-Allow-Origin": "http://127.0.0.1:5175",
                           "Access-Control-Allow-Credentials": "true",
                           "Access-Control-Allow-Headers": "Content-Type,X-Requested-With"}
                if request.method == "OPTIONS":
                    return route.fulfill(status=204, headers=headers)
                body = request.post_data_json if request.post_data else None
                response = api.client.request(request.method, url.path + (f"?{url.query}" if url.query else ""), json=body)
                if request.method not in ("GET", "HEAD"):
                    writes.append((request.method, url.path, body, response.status_code))
                if lose_next_court_reply and url.path.endswith("/court"):
                    lose_next_court_reply = False
                    return route.abort()  # Write committed but response was lost.
                if lose_next_fixture_reply and url.path.endswith("/fixture"):
                    lose_next_fixture_reply = False
                    return route.abort()
                return route.fulfill(status=response.status_code, body=response.content,
                                     content_type="application/json", headers=headers)
            route.abort()  # No external/live requests from this test browser.

        page.route("**/*", route_request)
        page.goto("http://127.0.0.1:5175/admin/americanos")
        page.wait_for_load_state("networkidle")
        expect(page.get_by_role("heading", name="Nuevo evento")).to_be_visible()
        expect(page.get_by_role("heading", name="Americanos", exact=True)).to_have_count(0)
        expect(page.get_by_role("button", name="Recargar lista", exact=True)).to_have_count(0)
        for target, toggle in [('dark', 'Cambiar a modo oscuro'), ('light', 'Cambiar a modo claro')]:
            if page.locator('html').get_attribute('data-admin') != target:
                page.get_by_role('button', name=toggle, exact=True).click()
            ratio = page.locator('[aria-current="step"]').evaluate('''element => {
                const rgb = color => (color.startsWith('#') ? color.slice(1).match(/../g).map(v => parseInt(v, 16)) : color.match(/[\\d.]+/g).slice(0, 3).map(Number)).map(v => v / 255).map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4);
                const light = color => rgb(color).reduce((sum, v, i) => sum + v * [.2126, .7152, .0722][i], 0);
                const a = light(getComputedStyle(element).backgroundColor);
                const b = light(getComputedStyle(element.lastElementChild).color);
                const contrast = (x,y) => (Math.max(x,y) + .05) / (Math.min(x,y) + .05);
                const style = getComputedStyle(document.documentElement);
                const muted = light(style.getPropertyValue('--color-ink-500').trim());
                return {
                  active: contrast(a,b),
                  mutedSurface: contrast(muted, light(style.getPropertyValue('--color-surface').trim())),
                  mutedCanvas: contrast(muted, light(style.getPropertyValue('--color-ink-100').trim())),
                };
            }''')
            assert all(value >= 4.5 for value in ratio.values()), (target, ratio)
        courts = page.get_by_role("button", name=re.compile(r"^Cancha [1-6]$"))
        assert courts.all_text_contents() and [button.get_attribute("aria-label") for button in courts.all()] == [
            "Cancha 4", "Cancha 5", "Cancha 6", "Cancha 1", "Cancha 2", "Cancha 3",
        ]
        boxes = [button.bounding_box() for button in courts.all()]
        assert boxes[0]["y"] == boxes[1]["y"] == boxes[2]["y"] < boxes[3]["y"]
        assert boxes[0]["x"] < boxes[1]["x"] < boxes[2]["x"]
        page.get_by_label("Nombre del nuevo evento").fill("Americano 3 y 6")
        page.get_by_role("combobox", name=re.compile("^Zonas")).select_option("2")
        for button in courts.all():
            button.click()
        expect(page.get_by_role("button", name="Crear borrador y agregar parejas")).to_be_disabled()
        for number in (3, 6):
            page.get_by_role("button", name=f"Cancha {number}", exact=True).click()
        for width in (320, 390, 768, 1280):
            page.set_viewport_size({"width": width, "height": 960})
            boxes = [button.bounding_box() for button in courts.all()]
            assert boxes[0]["y"] == boxes[1]["y"] == boxes[2]["y"] < boxes[3]["y"]
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), width
            if width == 1280:
                name_box = page.get_by_label('Nombre del nuevo evento').bounding_box()
                zones_box = page.get_by_role('combobox', name=re.compile('^Zonas')).bounding_box()
                stage_box = page.get_by_role('combobox', name=re.compile('^Inicio de eliminatorias')).bounding_box()
                assert name_box['x'] == zones_box['x'] == stage_box['x']
                assert name_box['y'] < zones_box['y'] < stage_box['y']
                assert name_box['x'] + name_box['width'] < boxes[0]['x']
                assert boxes[0]['width'] <= 124
                page.screenshot(path=str(Path(tempfile.gettempdir()) / 'americano-initial-layout.png'), full_page=True)
            if width == 390:
                page.screenshot(path=str(Path(tempfile.gettempdir()) / "americano-courts-mobile.png"), full_page=True)
        page.get_by_role("button", name="Crear borrador y agregar parejas").click()
        expect(page.get_by_role("heading", name=re.compile("02 · Parejas"))).to_be_visible()
        expect(page.get_by_role("heading", name="01 · Configuración")).not_to_be_visible()
        assert api.client.get(BASE).json()[0]["courts"] == [3, 6]
        print("PASS creation and court layout", flush=True)

        for index in range(1, 9):
            if index > 1:
                page.get_by_role("button", name="Agregar otra pareja").click()
            page.get_by_label(f"Pareja {index} · Jugador 1", exact=True).fill(f"Jugador {index}")
            page.get_by_label(f"Pareja {index} · Jugador 2", exact=True).fill(f"Compañero {index}")
        expect(page.get_by_role("button", name="Siguiente", exact=True)).to_be_disabled()
        page.get_by_role("button", name="Agregar 8 parejas", exact=True).click()
        expect(page.get_by_role("heading", name="02 · Parejas (8)", exact=True)).to_be_visible()
        page.get_by_role("button", name="Siguiente", exact=True).click()
        expect(page.get_by_role("heading", name="03 · Reparto y vista previa")).to_be_visible()
        page.get_by_role("button", name="Repartir aleatoriamente").click()
        expect(page.get_by_role("button", name="Repartir aleatoriamente")).to_be_enabled()
        choices = page.get_by_role("group", name="Seleccionar parejas de Zona A").get_by_role("button")
        for index, button in enumerate(choices.all()):
            if (button.get_attribute("aria-pressed") == "true") != (index < 4):
                button.click()
        if page.get_by_role("button", name="Guardar reparto").is_enabled():
            page.get_by_role("button", name="Guardar reparto").click()
        expect(page.get_by_role("button", name="Revisar fixture")).to_be_enabled()
        page.get_by_role("button", name="Revisar fixture").click()
        expect(page.get_by_role("heading", name="04 · Generar fixture")).to_be_visible()
        print("PASS pairs, random/manual zones and step persistence", flush=True)

        steps = page.get_by_role("navigation", name="Pasos del americano").get_by_role("button")
        steps.nth(0).click()
        page.get_by_role("button", name="Cancha 5", exact=True).click()
        expect(steps.nth(1)).to_be_disabled()
        page.get_by_role("button", name="Guardar configuración").click()
        expect(page.get_by_role("heading", name="01 · Configuración")).to_be_visible()
        expect(page.get_by_role("button", name="Guardar configuración")).to_be_disabled()
        page.get_by_role("button", name="Cancha 5", exact=True).click()
        page.get_by_role("button", name="Guardar configuración").click()
        expect(page.get_by_role("button", name="Guardar configuración")).to_be_disabled()
        steps.nth(3).click()
        screenshot = Path(tempfile.gettempdir()) / "americano-wizard-fixture.png"
        page.screenshot(path=str(screenshot), full_page=True)
        page.get_by_role("button", name="Generar fixture", exact=True).click()
        confirmation = page.get_by_role("dialog", name="Generar fixture", exact=True)
        expect(confirmation).to_be_visible()
        expect(confirmation.get_by_role("button", name="Volver a revisar")).to_be_focused()
        page.keyboard.press('Escape')
        expect(confirmation).to_have_count(0)
        assert not any(path.endswith('/fixture') for _, path, _, _ in writes)
        page.get_by_role("button", name="Generar fixture", exact=True).click()
        confirmation.screenshot(path=str(Path(tempfile.gettempdir()) / "americano-generation-dialog.png"))
        confirmation.get_by_role("button", name="Confirmar y abrir ronda", exact=True).click()
        expect(page.get_by_role("heading", name="Ronda 1/6", exact=True)).to_be_visible()
        expect(page.get_by_role("heading", name="Resumen del fixture")).to_have_count(0)
        expect(page.get_by_text("Cancha 3", exact=True)).to_be_visible()
        expect(page.get_by_text("Cancha 6", exact=True)).to_be_visible()
        print("PASS backwards configuration and assigned group courts", flush=True)

        detail = api.client.get(BASE).json()[0]
        event = api.client.get(f"{BASE}/{detail['id']}").json()
        assert event["courts"] == [3, 6] and event["total_rounds"] == 6
        event = _finish(api, event)
        preview = _preview(api, event)
        if preview["missing_slots"]:
            preview = _put(api, preview).json()
        confirmed = _confirm(api, preview)
        assert confirmed.status_code == 200, confirmed.text
        page.goto(f"http://127.0.0.1:5175/admin/americanos/{event['id']}/playoffs")
        page.wait_for_load_state("networkidle")
        final = page.get_by_role("combobox", name="Cancha de Final", exact=True)
        expect(final).to_have_value("3")
        assert final.locator("option").all_text_contents() == ["Cancha 3", "Cancha 6"]
        final.select_option("6")
        expect(final).to_have_value("6")
        expect(page.get_by_text("Cancha actualizada.", exact=True)).to_be_visible()
        lose_next_court_reply = True
        before_loss = len(writes)
        final.select_option("3")
        comparison = page.get_by_role("region", name="Comparación del cuadro", exact=True)
        expect(comparison).to_be_visible()
        expect(comparison.get_by_text("Cancha solicitada: 3 · Cancha guardada: 3. No se reenvió el cambio.", exact=True)).to_be_visible()
        assert len(writes) == before_loss + 1  # Never replay an uncertain write.
        comparison.get_by_role("button", name="Usar cuadro guardado", exact=True).click()
        expect(final).to_have_value("3")
        expect(final).to_be_enabled()
        semifinal = page.get_by_role("article", name="Semifinal 1", exact=True)
        semifinal.get_by_role("textbox").first.fill("6")
        expect(final).to_be_disabled()
        semifinal.get_by_role("button", name="Cancelar", exact=True).click()
        expect(final).to_be_enabled()

        # Explicit save flow: digit A -> digit B -> Save -> next playable match.
        first_input, second_input = semifinal.get_by_role("textbox").all()
        assert first_input.get_attribute('maxlength') == '1'
        first_input.fill('')
        first_input.fill('6')
        expect(second_input).to_be_focused()
        second_input.fill('5')
        expect(semifinal.get_by_role('button', name='Guardar resultado', exact=True)).to_be_disabled()
        expect(semifinal.get_by_text('Resultado inválido. Usá 6-0 a 6-4, 7-5 o 7-6, o sus inversos.')).to_be_visible()
        second_input.fill('')
        second_input.fill('0')
        first_save = semifinal.get_by_role('button', name='Guardar resultado', exact=True)
        expect(first_save).to_be_focused()
        page.keyboard.press('Enter')
        semifinal_two = page.get_by_role('article', name='Semifinal 2', exact=True)
        expect(semifinal_two.get_by_role('textbox').first).to_be_focused()
        semifinal_two.get_by_role('textbox').first.fill('7')
        expect(semifinal_two.get_by_role('textbox').nth(1)).to_be_focused()
        semifinal_two.get_by_role('textbox').nth(1).fill('5')
        semifinal_two.get_by_role('button', name='Guardar resultado', exact=True).click()
        final_match = page.get_by_role('article', name='Final', exact=True)
        expect(final_match.get_by_role('textbox').first).to_be_focused()
        final_match.get_by_role('textbox').first.fill('9')
        expect(final_match.get_by_role('textbox').first).to_have_value('')
        final_match.get_by_role('textbox').first.fill('7')
        second_final = final_match.get_by_role('textbox').nth(1)
        second_final.evaluate('element => { const data = new DataTransfer(); data.setData("text", "10"); element.dispatchEvent(new ClipboardEvent("paste", {clipboardData: data, bubbles: true, cancelable: true})); }')
        expect(second_final).to_have_value('')
        second_final.fill('6')
        final_match.get_by_role('button', name='Guardar resultado', exact=True).click()
        expect(page.get_by_role('region', name='Campeón', exact=True)).to_be_visible()
        champion = api.client.get(f"{BASE}/{event['id']}/playoffs").json()['champion']
        page.get_by_role('button', name='Volver a Americanos', exact=True).click()
        expect(page.get_by_role('columnheader', name='Campeones', exact=True)).to_be_visible()
        expect(page.get_by_role('columnheader', name='Grupos guardados', exact=True)).to_have_count(0)
        row = page.get_by_role('row').filter(has_text='Americano 3 y 6')
        expect(row).to_contain_text(f"{champion['player1_name']} / {champion['player2_name']}")
        for width in (390, 768, 1280):
            page.set_viewport_size({"width": width, "height": 960})
            page.goto(f"http://127.0.0.1:5175/admin/americanos/{event['id']}/configuracion")
            page.wait_for_load_state("networkidle")
            page.get_by_role("navigation", name="Pasos del americano").get_by_role("button").first.click()
            expect(page.get_by_role("heading", name="01 · Configuración")).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), width

        # No intermediate setup screen even when the fixture response is lost.
        retry_draft = create_event(api, name='Respuesta perdida al generar')
        for index in range(2):
            retry_draft = add_registration(api, retry_draft, first=f'Retry {index}', second=f'B {index}')
        page.goto(f"http://127.0.0.1:5175/admin/americanos/{retry_draft['id']}/configuracion")
        page.wait_for_load_state('networkidle')
        page.get_by_role('navigation', name='Pasos del americano').get_by_role('button').nth(3).click()
        page.get_by_role('button', name='Generar fixture', exact=True).click()
        lose_next_fixture_reply = True
        page.get_by_role('dialog', name='Generar fixture').get_by_role('button', name='Confirmar y abrir ronda').click()
        expect(page.get_by_role('heading', name='Ronda 1/1', exact=True)).to_be_visible()
        assert len([path for _, path, _, _ in writes if path == f"{BASE}/{retry_draft['id']}/fixture"]) == 1

        # Two one-pair zones have no group matches: go directly to qualification.
        zero = create_event(api, name='Sin rondas de grupos', zone_count=2)
        for index in range(2):
            zero = add_registration(api, zero, first=f'Zero {index}', second=f'Z {index}')
        response = api.client.put(f"{BASE}/{zero['id']}/zones", json={
            'expected_revision': zero['revision'], 'zone_count': 2,
            'zone_a_registration_ids': [zero['registrations'][0]['id']],
        })
        assert response.status_code == 200, response.text
        page.goto(f"http://127.0.0.1:5175/admin/americanos/{zero['id']}/configuracion")
        page.wait_for_load_state('networkidle')
        page.get_by_role('navigation', name='Pasos del americano').get_by_role('button').nth(3).click()
        page.get_by_role('button', name='Generar fixture', exact=True).click()
        page.get_by_role('dialog', name='Generar fixture').get_by_role('button', name='Confirmar y revisar clasificados').click()
        expect(page.get_by_role('heading', name='Clasificados', exact=True)).to_be_visible()
        assert not errors, errors
        assert not native_dialogs, native_dialogs
        assert all(status < 300 for _, _, _, status in writes), writes
        browser.close()
        print(json.dumps({"result": "PASS", "writes": len(writes), "viewports": [390, 768, 1280], "screenshot": str(screenshot)}))


if __name__ == "__main__":
    run()
