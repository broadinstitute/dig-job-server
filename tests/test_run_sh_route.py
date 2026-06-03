def test_serves_run_sh_with_baseurl_substituted(api_client):
    res = api_client.get("/run.sh")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/x-shellscript")
    body = res.text
    assert body.startswith("#!/usr/bin/env bash")
    assert "{{GWAS_CE_BASE_URL}}" not in body
    assert "testserver" in body or "http" in body
