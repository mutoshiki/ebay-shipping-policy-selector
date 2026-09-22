from __future__ import annotations

import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = "http://127.0.0.1:4173/#judge"
OUT = Path("qa-artifacts")
OUT.mkdir(exist_ok=True)

results = []
failures = []


def record(name, ok, detail=None):
    row = {"name": name, "ok": bool(ok)}
    if detail is not None:
        row["detail"] = detail
    results.append(row)
    if not ok:
        failures.append(row)


def assert_eq(actual, expected, msg=""):
    if actual != expected:
        raise AssertionError(f"{msg} expected={expected!r} actual={actual!r}")


def assert_in(needle, haystack, msg=""):
    if needle not in haystack:
        raise AssertionError(f"{msg} missing {needle!r} in {haystack!r}")


def setup_page(browser, width=1280, height=900, scheme="light", touch=False):
    context = browser.new_context(
        viewport={"width": width, "height": height},
        color_scheme=scheme,
        has_touch=touch,
        is_mobile=touch,
    )
    page = context.new_page()
    page_errors = []
    console_errors = []
    page.on("pageerror", lambda e: page_errors.append(str(e)))
    page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
    page.goto(BASE, wait_until="load")
    page.wait_for_selector("#judgeForm")
    return context, page, page_errors, console_errors


def fill_estimate(page, *, price, base, packing=0, custom=0, dims=None):
    page.fill("#baseWeight", str(base))
    page.fill("#packingWeight", str(packing))
    page.fill("#customExtra", str(custom))
    page.fill("#priceUsd", str(price))
    if dims:
        details = page.locator("details.dimension-disclosure")
        if not details.get_attribute("open"):
            details.locator("summary").click()
        page.fill("#boxLength", str(dims[0]))
        page.fill("#boxWidth", str(dims[1]))
        page.fill("#boxHeight", str(dims[2]))
    page.click("#judgeButton")
    page.wait_for_timeout(100)


def snapshot_result(page):
    def txt(sel):
        return (page.locator(sel).text_content() or "").strip()
    return {
        "status": txt("#resultStatus"),
        "policy": txt("#policyName"),
        "rateTable": txt("#rateTableQuick"),
        "weight": txt("#resultWeight"),
        "weightTier": txt("#resultWeightTier"),
        "priceTier": txt("#resultPriceTier"),
        "manual": "" if page.locator("#resultManual").is_hidden() else txt("#resultManual"),
        "warning": "" if page.locator("#resultWarning").is_hidden() else txt("#resultWarning"),
    }


def run_case(browser, name, expected, *, price, base, packing=0, custom=0, dims=None, screenshot=None):
    context, page, page_errors, console_errors = setup_page(browser)
    try:
        fill_estimate(page, price=price, base=base, packing=packing, custom=custom, dims=dims)
        got = snapshot_result(page)
        for key, value in expected.items():
            if isinstance(value, tuple) and value and value[0] == "contains":
                assert_in(value[1], got[key], f"{name}:{key}")
            else:
                assert_eq(got[key], value, f"{name}:{key}")
        if page_errors:
            raise AssertionError(f"page errors: {page_errors}")
        if console_errors:
            raise AssertionError(f"console errors: {console_errors}")
        if screenshot:
            page.screenshot(path=str(OUT / screenshot), full_page=True)
        record(name, True, got)
    except Exception as exc:
        page.screenshot(path=str(OUT / f"FAIL-{name}.png"), full_page=True)
        record(name, False, str(exc))
    finally:
        context.close()


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    # Load / layout smoke.
    for width, height, scheme, touch in [
        (1280, 900, "light", False),
        (1280, 900, "dark", False),
        (390, 844, "light", True),
        (390, 844, "dark", True),
        (360, 800, "light", True),
    ]:
        name = f"smoke-{width}x{height}-{scheme}"
        context, page, page_errors, console_errors = setup_page(browser, width, height, scheme, touch)
        try:
            metrics = page.evaluate("""() => ({
                title: document.title,
                bodyText: document.body.innerText.length,
                overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
                judgeVisible: !document.querySelector('#view-judge').hidden,
                navButtons: document.querySelectorAll('.nav-button').length
            })""")
            assert_in("Film Camera Shipping Guide", metrics["title"], name)
            if metrics["bodyText"] < 500:
                raise AssertionError(f"body too short: {metrics}")
            if metrics["overflowX"] > 1:
                raise AssertionError(f"horizontal overflow: {metrics['overflowX']}")
            assert_eq(metrics["judgeVisible"], True, name)
            assert_eq(metrics["navButtons"], 3, name)
            if page_errors or console_errors:
                raise AssertionError(f"errors page={page_errors} console={console_errors}")
            page.screenshot(path=str(OUT / f"{name}.png"), full_page=False)
            record(name, True, metrics)
        except Exception as exc:
            page.screenshot(path=str(OUT / f"FAIL-{name}.png"), full_page=True)
            record(name, False, str(exc))
        finally:
            context.close()

    # Initial state should not invent package weight, and mobile actions must not cover the form.
    context, page, page_errors, console_errors = setup_page(browser, 390, 844, "light", True)
    try:
        base = page.input_value("#baseWeight")
        packing = page.input_value("#packingWeight")
        calculated = (page.locator("#calculatedWeight").text_content() or "").strip()
        position = page.evaluate("getComputedStyle(document.querySelector('.judge-action-area')).position")
        assert_eq(base, "", "initial base")
        assert_eq(packing, "", "initial packing")
        assert_eq(calculated, "—", "initial calculated weight")
        assert_eq(position, "static", "mobile judge action position")
        if page_errors or console_errors:
            raise AssertionError(f"errors page={page_errors} console={console_errors}")
        record("initial-empty-weight-mobile-flow", True, {"calculated": calculated, "position": position})
    except Exception as exc:
        page.screenshot(path=str(OUT / "FAIL-initial-state.png"), full_page=True)
        record("initial-empty-weight-mobile-flow", False, str(exc))
    finally:
        context.close()

    # Switching/clearing products must not reuse packaging state from a previous item.
    context, page, page_errors, console_errors = setup_page(browser)
    try:
        page.fill("#productSearch", "DG-2")
        page.wait_for_selector("#searchSuggestions:not([hidden])")
        page.locator("#searchSuggestions .suggestion").first.click()
        page.fill("#customExtra", "45")
        details = page.locator("details.dimension-disclosure")
        if not details.get_attribute("open"):
            details.locator("summary").click()
        page.fill("#boxLength", "23")
        page.fill("#boxWidth", "15")
        page.fill("#boxHeight", "7")
        page.locator('input[name="weightMode"][value="measured"]').check()
        page.fill("#measuredWeight", "999")

        page.fill("#productSearch", "AS-1")
        page.wait_for_selector("#searchSuggestions:not([hidden])")
        page.locator("#searchSuggestions .suggestion").first.click()
        assert_eq(page.input_value("#customExtra"), "0", "switch custom extra")
        assert_eq(page.input_value("#measuredWeight"), "", "switch measured")
        assert_eq(page.input_value("#boxLength"), "", "switch box length")
        assert_eq(page.input_value("#boxWidth"), "", "switch box width")
        assert_eq(page.input_value("#boxHeight"), "", "switch box height")
        assert_eq(page.locator('input[name="weightMode"][value="estimate"]').is_checked(), True, "switch estimate mode")

        page.click("#clearSelected")
        assert_eq(page.input_value("#baseWeight"), "", "clear base")
        assert_eq(page.input_value("#packingWeight"), "", "clear packing")
        assert_eq((page.locator("#calculatedWeight").text_content() or "").strip(), "—", "clear calculated")
        if page_errors or console_errors:
            raise AssertionError(f"errors page={page_errors} console={console_errors}")
        record("item-switch-clear-resets-package-state", True)
    except Exception as exc:
        page.screenshot(path=str(OUT / "FAIL-item-reset.png"), full_page=True)
        record("item-switch-clear-resets-package-state", False, str(exc))
    finally:
        context.close()

    # Core policy matrix through rendered UI.
    run_case(
        browser, "p0-49-440-to-600",
        {"status": "判定完了", "policy": "CAM-US-0-49-600G", "rateTable": "INT-AP-SPK-0600G-V3",
         "weightTier": ("contains", "600g枠"), "priceTier": ("contains", "$0–49.99")},
        price=34.99, base=300, packing=140, screenshot="case-440-34.99.png"
    )
    run_case(
        browser, "p50-99-440-candidate-600",
        {"status": "Policy作成候補", "policy": "CAM-US-50-99-600G（候補）", "rateTable": "INT-AP-SPK-0600G-V3",
         "weightTier": ("contains", "600g枠"), "manual": ("contains", "確定送料として使用しない")},
        price=84.99, base=300, packing=140, screenshot="case-440-84.99.png"
    )
    run_case(
        browser, "p50-99-over600-to900",
        {"status": "判定完了", "policy": "CAM-US-50-99-900G", "rateTable": "INT-AP-SPK-0900G-V3",
         "weightTier": ("contains", "900g枠")},
        price=84.99, base=600.1, packing=0
    )
    run_case(
        browser, "p100-129-650-to700",
        {"status": "判定完了", "policy": "CAM-US-100-129-700G", "rateTable": "INT-AP-SPK-0700G-V3",
         "weightTier": ("contains", "700g枠")},
        price=119.99, base=650, packing=0
    )
    run_case(
        browser, "p130-149-440-to700",
        {"status": "判定完了", "policy": "CAM-US-130-149-700G", "rateTable": "INT-AP-SPK-0700G-V3",
         "weightTier": ("contains", "700g枠")},
        price=130, base=440, packing=0
    )
    run_case(
        browser, "volume-301.9-to600",
        {"status": "判定完了", "policy": "CAM-US-0-49-600G", "rateTable": "INT-AP-SPK-0600G-V3",
         "weight": ("contains", "301.9g"), "weightTier": ("contains", "600g枠")},
        price=34.99, base=100, packing=0, dims=(23, 15, 7), screenshot="case-volume.png"
    )

    # Price rounding boundaries.
    run_case(
        browser, "price-round-49.999-to50",
        {"status": "Policy作成候補", "policy": "CAM-US-50-99-600G（候補）",
         "rateTable": "INT-AP-SPK-0600G-V3"},
        price=49.999, base=440, packing=0
    )
    run_case(
        browser, "price-round-99.999-to100",
        {"status": "判定完了", "policy": "CAM-US-100-129-600G",
         "rateTable": "INT-AP-SPK-0600G-V3"},
        price=99.999, base=440, packing=0
    )

    # Out of configured ranges should be explicit, not a wrong policy.
    run_case(
        browser, "price-150-manual",
        {"status": "Policy要確認", "policy": "US Policy未設定", "manual": ("contains", "$0〜149.99")},
        price=150, base=440, packing=0
    )
    run_case(
        browser, "weight-over1000-manual",
        {"status": "Policy要確認", "policy": "US Policy未設定", "manual": ("contains", "1000gを超えています")},
        price=34.99, base=1000.1, packing=0
    )

    # Partial dimensions validation.
    context, page, page_errors, console_errors = setup_page(browser)
    try:
        page.fill("#baseWeight", "100")
        page.fill("#packingWeight", "0")
        page.fill("#priceUsd", "34.99")
        page.locator("details.dimension-disclosure summary").click()
        page.fill("#boxLength", "23")
        page.click("#judgeButton")
        page.wait_for_timeout(100)
        toast = page.locator("#toast").inner_text().strip()
        if not page.locator("#resultContent").is_hidden():
            raise AssertionError("result was produced with incomplete dimensions")
        assert_in("3つすべて", toast, "partial dims toast")
        record("partial-dimensions-blocked", True, {"toast": toast})
    except Exception as exc:
        page.screenshot(path=str(OUT / "FAIL-partial-dimensions.png"), full_page=True)
        record("partial-dimensions-blocked", False, str(exc))
    finally:
        context.close()

    # Search -> item selection -> auto-population.
    context, page, page_errors, console_errors = setup_page(browser)
    try:
        page.fill("#productSearch", "DG-2")
        page.wait_for_selector("#searchSuggestions:not([hidden])")
        suggestion_count = page.locator("#searchSuggestions .suggestion").count()
        if suggestion_count < 1:
            raise AssertionError("no DG-2 search suggestions")
        page.locator("#searchSuggestions .suggestion").first.click()
        selected = page.locator("#selectedItemCard").inner_text()
        base = float(page.input_value("#baseWeight"))
        packing = float(page.input_value("#packingWeight"))
        if "DG-2" not in selected:
            raise AssertionError(f"wrong selected item: {selected}")
        if base <= 0 or packing <= 0:
            raise AssertionError(f"auto values invalid base={base} packing={packing}")
        page.fill("#priceUsd", "39.99")
        page.click("#judgeButton")
        page.wait_for_timeout(100)
        got = snapshot_result(page)
        if page_errors or console_errors:
            raise AssertionError(f"errors page={page_errors} console={console_errors}")
        record("search-select-autofill", True, {"suggestions": suggestion_count, "base": base, "packing": packing, "result": got})
    except Exception as exc:
        page.screenshot(path=str(OUT / "FAIL-search-select.png"), full_page=True)
        record("search-select-autofill", False, str(exc))
    finally:
        context.close()

    # History candidate retention + restore.
    context, page, page_errors, console_errors = setup_page(browser)
    try:
        fill_estimate(page, price=84.99, base=300, packing=140)
        page.get_by_role("button", name="履歴を見る").click()
        page.wait_for_selector("#view-history:not([hidden])")
        first = page.locator("#historyList .history-card").first
        card_text = first.inner_text()
        assert_in("CAM-US-50-99-600G（候補）", card_text, "history candidate")
        assert_in("INT-AP-SPK-0600G-V3", card_text, "history rate")
        first.get_by_role("button", name="条件を再利用").click()
        page.wait_for_selector("#view-judge:not([hidden])")
        page.wait_for_timeout(200)
        got = snapshot_result(page)
        assert_eq(got["policy"], "CAM-US-50-99-600G（候補）", "restored candidate")
        record("history-candidate-restore", True, {"card": card_text[:300], "result": got})
    except Exception as exc:
        page.screenshot(path=str(OUT / "FAIL-history.png"), full_page=True)
        record("history-candidate-restore", False, str(exc))
    finally:
        context.close()

    # Current-settings panel must not contain obsolete weight-only policy setup.
    context, page, page_errors, console_errors = setup_page(browser)
    try:
        page.locator('.nav-button[data-view="tools"]').click()
        page.wait_for_selector("#view-tools:not([hidden])")
        snapshot = (page.locator("#codexPromptText").text_content() or "").strip()
        assert_in("440g / $34.99 → CAM-US-0-49-600G", snapshot, "current settings")
        if "CAM0100G-V3\nCAM0200G-V3" in snapshot:
            raise AssertionError("obsolete V3-only policy creation prompt is still visible")
        record("tools-current-policy-snapshot", True, {"chars": len(snapshot)})
    except Exception as exc:
        page.screenshot(path=str(OUT / "FAIL-tools-snapshot.png"), full_page=True)
        record("tools-current-policy-snapshot", False, str(exc))
    finally:
        context.close()

    # Theme toggle and mobile rendered result overflow.
    context, page, page_errors, console_errors = setup_page(browser, 390, 844, "light", True)
    try:
        before = page.evaluate("document.documentElement.dataset.theme || 'light'")
        page.click("#themeToggle")
        after = page.evaluate("document.documentElement.dataset.theme || 'light'")
        if before == after:
            raise AssertionError(f"theme did not change: {before}")
        fill_estimate(page, price=34.99, base=300, packing=140)
        metrics = page.evaluate("""() => {
          const r = document.querySelector('#resultPanel').getBoundingClientRect();
          const p = document.querySelector('#policyName').getBoundingClientRect();
          return {
            overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
            resultLeft: r.left, resultRight: r.right, viewport: innerWidth,
            policyLeft: p.left, policyRight: p.right
          }
        }""")
        if metrics["overflowX"] > 1:
            raise AssertionError(f"mobile horizontal overflow {metrics}")
        if metrics["resultLeft"] < -1 or metrics["resultRight"] > metrics["viewport"] + 1:
            raise AssertionError(f"result panel outside viewport {metrics}")
        page.screenshot(path=str(OUT / "mobile-result-390.png"), full_page=True)
        record("mobile-result-layout-theme", True, metrics)
    except Exception as exc:
        page.screenshot(path=str(OUT / "FAIL-mobile-result.png"), full_page=True)
        record("mobile-result-layout-theme", False, str(exc))
    finally:
        context.close()


    # Every secondary view must render without JS/console errors.
    context, page, page_errors, console_errors = setup_page(browser)
    try:
        page.locator('.nav-button[data-view="tools"]').click()
        page.wait_for_selector('#view-tools:not([hidden])')
        for target in ["database", "genres", "data"]:
            page.locator(f'[data-open-view="{target}"]').first.click()
            page.wait_for_selector(f'#view-{target}:not([hidden])')
            page.locator('[data-open-view="tools"]').first.click()
            page.wait_for_selector('#view-tools:not([hidden])')
        page.locator('.nav-button[data-view="history"]').click()
        page.wait_for_selector('#view-history:not([hidden])')
        if page_errors or console_errors:
            raise AssertionError(f"errors page={page_errors} console={console_errors}")
        record("all-secondary-views-render", True)
    except Exception as exc:
        page.screenshot(path=str(OUT / "FAIL-secondary-views.png"), full_page=True)
        record("all-secondary-views-render", False, str(exc))
    finally:
        context.close()

    # Search with existing history but zero matches must show an explicit empty result,
    # rather than leaving the history pane blank.
    context, page, page_errors, console_errors = setup_page(browser)
    try:
        fill_estimate(page, price=34.99, base=300, packing=140)
        page.get_by_role("button", name="履歴を見る").click()
        page.wait_for_selector("#view-history:not([hidden])")
        page.fill("#historySearch", "__no_history_match__")
        page.wait_for_timeout(250)
        empty = page.locator("#historyEmpty")
        if empty.is_hidden():
            raise AssertionError("history zero-match state is hidden")
        empty_text = empty.inner_text().strip()
        assert_in("一致", empty_text, "history zero-match message")
        if page_errors or console_errors:
            raise AssertionError(f"errors page={page_errors} console={console_errors}")
        record("history-search-zero-state", True, {"message": empty_text})
    except Exception as exc:
        page.screenshot(path=str(OUT / "FAIL-history-search-zero.png"), full_page=True)
        record("history-search-zero-state", False, str(exc))
    finally:
        context.close()

    # Corrupt-but-valid JSON arrays in localStorage must not crash app startup.
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page_errors = []
    console_errors = []
    page.on("pageerror", lambda e: page_errors.append(str(e)))
    page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
    try:
        page.add_init_script("""() => {
          localStorage.setItem('filmCameraMeasurements', JSON.stringify([null, 123, {}, {name:'ok', id:'x'}]));
          localStorage.setItem('filmCameraJudgementHistoryV1', JSON.stringify([null, 123, {}, {id:'h-ok', product:'ok', weight:100, createdAt:new Date().toISOString()}]));
        }""")
        page.goto(BASE, wait_until="load")
        page.wait_for_selector("#judgeForm")
        page.wait_for_timeout(100)
        if page_errors or console_errors:
            raise AssertionError(f"errors page={page_errors} console={console_errors}")
        record("malformed-storage-arrays-safe", True)
    except Exception as exc:
        page.screenshot(path=str(OUT / "FAIL-malformed-storage.png"), full_page=True)
        record("malformed-storage-arrays-safe", False, str(exc))
    finally:
        context.close()

    # Measured mode should drive policy selection and suppress estimate warnings.
    context, page, page_errors, console_errors = setup_page(browser)
    try:
        page.locator('input[name="weightMode"][value="measured"]').check()
        page.fill("#measuredWeight", "440")
        page.fill("#priceUsd", "34.99")
        page.click("#judgeButton")
        page.wait_for_timeout(100)
        got = snapshot_result(page)
        assert_eq(got["policy"], "CAM-US-0-49-600G", "measured policy")
        if "推定重量による判定" in got["warning"]:
            raise AssertionError(f"estimate warning shown in measured mode: {got['warning']}")
        if page_errors or console_errors:
            raise AssertionError(f"errors page={page_errors} console={console_errors}")
        record("measured-mode-policy", True, got)
    except Exception as exc:
        page.screenshot(path=str(OUT / "FAIL-measured-mode.png"), full_page=True)
        record("measured-mode-policy", False, str(exc))
    finally:
        context.close()

    # Volumetric weight must still override a smaller measured weight.
    context, page, page_errors, console_errors = setup_page(browser)
    try:
        page.locator('input[name="weightMode"][value="measured"]').check()
        page.fill("#measuredWeight", "100")
        page.fill("#priceUsd", "34.99")
        details = page.locator("details.dimension-disclosure")
        if not details.get_attribute("open"):
            details.locator("summary").click()
        page.fill("#boxLength", "23")
        page.fill("#boxWidth", "15")
        page.fill("#boxHeight", "7")
        page.click("#judgeButton")
        page.wait_for_timeout(100)
        got = snapshot_result(page)
        assert_eq(got["policy"], "CAM-US-0-49-600G", "measured volumetric policy")
        assert_in("301.9g", got["weight"], "measured volumetric weight")
        if page_errors or console_errors:
            raise AssertionError(f"errors page={page_errors} console={console_errors}")
        record("measured-volume-overrides", True, got)
    except Exception as exc:
        page.screenshot(path=str(OUT / "FAIL-measured-volume.png"), full_page=True)
        record("measured-volume-overrides", False, str(exc))
    finally:
        context.close()

    browser.close()

report = {
    "passed": sum(1 for r in results if r["ok"]),
    "failed": len(failures),
    "total": len(results),
    "results": results,
}
(OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "report.md").write_text(
    "# Browser QA\n\n"
    + f"- Passed: {report['passed']}\n- Failed: {report['failed']}\n- Total: {report['total']}\n\n"
    + "\n".join(f"- {'PASS' if r['ok'] else 'FAIL'} — {r['name']}: {r.get('detail','')}" for r in results),
    encoding="utf-8",
)
print(json.dumps(report, ensure_ascii=False, indent=2))
if failures:
    raise SystemExit(1)
