def test_health_endpoint(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["llm_mode"] == "offline"


def test_upload_rejects_bad_extension(client):
    resp = client.post("/api/reports", files={"file": ("report.docx", b"hello", "application/octet-stream")})
    assert resp.status_code == 400


def test_upload_rejects_empty_file(client):
    resp = client.post("/api/reports", files={"file": ("report.txt", b"", "text/plain")})
    assert resp.status_code == 400


def test_upload_and_retrieve_report(client, sample_text):
    resp = client.post(
        "/api/reports",
        files={"file": ("greenfield_brsr.txt", sample_text.encode("utf-8"), "text/plain")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["company_name"] == "Greenfield Textiles Limited"
    assert body["extracted_data"]["environment"]["scope1_emissions_tco2e"] == 12500.0
    assert 0 <= body["esg_score"]["overall_score"] <= 100
    assert body["carbon_metrics"]["total_scope12_tco2e"] == 20700.0

    # Regression guard: computed properties (disclosure_completeness etc.) must
    # actually be present on the serialized JSON the frontend consumes, not
    # just accessible on the Python object server-side.
    assert len(body["extracted_data"]["principles"]) == 9
    for principle in body["extracted_data"]["principles"]:
        assert "disclosure_completeness" in principle
        assert isinstance(principle["disclosure_completeness"], (int, float))
    assert "total_scope12_emissions" in body["extracted_data"]["environment"]
    assert "carbon_intensity_per_revenue" in body["extracted_data"]["environment"]

    report_id = body["id"]

    list_resp = client.get("/api/reports")
    assert list_resp.status_code == 200
    assert any(r["id"] == report_id for r in list_resp.json())

    detail_resp = client.get(f"/api/reports/{report_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == report_id


def test_get_missing_report_404s(client):
    resp = client.get("/api/reports/999999")
    assert resp.status_code == 404


def test_narrative_summary_endpoint(client, sample_text):
    upload = client.post(
        "/api/reports",
        files={"file": ("greenfield_brsr.txt", sample_text.encode("utf-8"), "text/plain")},
    )
    report_id = upload.json()["id"]

    resp = client.get(f"/api/reports/{report_id}/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "offline"
    assert "summary" in body and len(body["summary"]) > 0


def test_chat_flow(client, sample_text):
    upload = client.post(
        "/api/reports",
        files={"file": ("greenfield_brsr.txt", sample_text.encode("utf-8"), "text/plain")},
    )
    report_id = upload.json()["id"]

    resp = client.post(f"/api/reports/{report_id}/chat", json={"message": "What were the Scope 1 emissions?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "offline"
    assert body["reply"]

    history_resp = client.get(f"/api/reports/{report_id}/chat")
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


def test_chat_on_missing_report_404s(client):
    resp = client.post("/api/reports/999999/chat", json={"message": "hi"})
    assert resp.status_code == 404


def test_delete_report(client, sample_text):
    upload = client.post(
        "/api/reports",
        files={"file": ("greenfield_brsr.txt", sample_text.encode("utf-8"), "text/plain")},
    )
    report_id = upload.json()["id"]

    del_resp = client.delete(f"/api/reports/{report_id}")
    assert del_resp.status_code == 204

    get_resp = client.get(f"/api/reports/{report_id}")
    assert get_resp.status_code == 404
