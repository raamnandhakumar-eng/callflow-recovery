def test_product_landing_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Recruiter demo" in response.text
    assert "Run the demo" in response.text
    assert "simulated" in response.text.lower()
    assert "/dashboard/northstar-hvac" in response.text
    assert "/ready" in response.text


def test_product_dashboard_page(client):
    response = client.get("/dashboard/northstar-hvac")
    assert response.status_code == 200
    assert "AI Workflow Operations" in response.text
    assert "Run the complete workflow" in response.text
    assert "Knowledge gaps" in response.text
    assert "Estimated booking value" in response.text
    assert "This is not realized revenue" in response.text
