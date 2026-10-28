"""Smoke test the running local stack; leave the persistent demo unresolved."""

import json
from pathlib import Path
import tempfile
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 960})
    page.set_default_timeout(30000)
    expect.set_options(timeout=30000)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))

    def local_only(route):
        url = urlsplit(route.request.url)
        if url.hostname == "localhost" and url.port in (5175, 8010):
            route.continue_()
        else:
            route.abort()

    page.route("**/*", local_only)
    health = page.request.get("http://localhost:8010/health").json()
    assert health["status"] == "ok" and health["cloudinary"] is False
    page.goto("http://localhost:5175/admin/americanos/1/clasificados")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Email", exact=True).fill("admin@liga.local")
    page.get_by_label("Contraseña", exact=True).fill("Liga-local-2026!")
    page.get_by_role("button", name="Entrar", exact=True).click()
    expect(page.get_by_role("heading", name="Clasificados", exact=True)).to_be_visible()
    expect(page.get_by_text("Demo empate puestos 1 y 2", exact=True)).to_be_visible()
    page.get_by_role("button", name="Resolver empates", exact=True).click()
    dialog = page.get_by_role("dialog", name="Resolver empates", exact=True)
    expect(dialog).to_be_visible()
    assert dialog.get_by_role("combobox").count() == 2
    expect(dialog.get_by_role("combobox", name="Zona A · plaza 1")).to_have_value("")
    expect(dialog.get_by_role("combobox", name="Zona A · plaza 2")).to_have_value("")
    screenshot = Path(tempfile.gettempdir()) / "liga-local-demo-tie.png"
    page.screenshot(path=str(screenshot), full_page=True)
    dialog.get_by_role("button", name="Volver", exact=True).click()
    assert not errors, errors
    browser.close()
    print(json.dumps({"result": "PASS", "backend": "local PostgreSQL", "demo": "left unresolved", "screenshot": str(screenshot)}))
