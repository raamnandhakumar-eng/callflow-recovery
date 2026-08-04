def test_product_landing_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Turn every inbound call" in response.text
    assert "/dashboard/northstar-hvac" in response.text


def test_product_dashboard_page(client):
    response = client.get("/dashboard/northstar-hvac")
    assert response.status_code == 200
    assert "Revenue Operations" in response.text
    assert "Run the complete workflow" in response.text
    assert "Knowledge gaps" in response.text
