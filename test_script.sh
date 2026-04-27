#!/bin/sh

# Ideas: Lunomeda.com
# Weddings:
# https://www.bridesbydeanna.com/copy-of-gallery
# https://www.herdefinition.co.uk/bridal-beauty
# https://www.braidsbyneishaa.com/womens-styles
# https://www.braidsbyneishaa.com/mens-gallery
# https://www.themercyseatbeauty.com/
# https://app.acuityscheduling.com/schedule.php?owner=11256835
# Hard refresh: Mac: Cmd + Shift + R

# https://www.facebook.com/hashtag/austinbraids

# echo "------------------------------------------------------------ prepare database tables ------------------------------------------------------------"
python3 -m rds_engine.init_tables drop_all \
    provider_profile \
    provider_fact_record \
    provider_fact_kv \
    capsule_filter_keys \
    capsule_update_queue \
    bootstrap_url_queue \
    community_post \
    community_comment \
    weekly_squeezein_availability \
    app_user \
    app_session \
    app_user_url_profile \
    image_asset \
    image_bucket \
    image_asset_subject \
    image_asset_audit \
    image_asset_audit_kv \
    image_asset_stage_state \
    provider_spotlight_current \
    fact_key_catalog \
    provider_fact_bool_current \
    provider_fact_bool_current \
    provider_style_current \
    style_review_queue \
    provider_style_override \
    scraped_html_archive
python3 -m rds_engine.init_tables init

python3 -m rds_engine.init_tables drop_all \
    style_catalog \
    style_alias
python3 -m rds_engine.init_tables init

python3 -m rds_engine.init_tables drop_all provider_profile provider_fact_record provider_fact_kv capsule_filter_keys capsule_update_queue image_bucket image_asset image_asset_subject image_asset_audit image_asset_audit_kv provider_spotlight_current
python3 -m rds_engine.init_tables init
python3 -m rds_engine.init_tables show provider_profile provider_fact_record provider_fact_kv capsule_filter_keys capsule_update_queue image_bucket image_asset image_asset_subject image_asset_audit image_asset_audit_kv provider_spotlight_current --n 20

python3 -m rds_engine.init_tables show app_user app_session --n 1
python3 -m rds_engine.init_tables show capsule_update_queue bootstrap_url_queue --n 10
python3 -m rds_engine.init_tables show provider_fact_bool_current --n 20
python3 -m tools.endpoints_cli processqueuedupdate --debug
python3 -m rds_engine.init_tables drop_all image_asset_subject image_asset_audit image_asset_audit_kv provider_spotlight_current

# echo "------------------------------------------------------------ processurls ------------------------------------------------------------"
python3 -m meaning_engine.cli.process_urls --limit 10 --write-db --debug
python3 -m meaning_engine.cli.process_urls --url "https://sweetiepies.as.me/schedule/1ee45e03"  --write-db --debug --force

# echo "------------------------------------------------------------ image scoring ------------------------------------------------------------"
python3 -m geometry_engine.cli.process_image_assets --output "./output/test_output" --only-missing-current-audit --write-db --debug --limit 5
python3 -m geometry_engine.cli.process_image_assets --input "./geometry_engine/fixtures/test_pictures_small/" --output "./geometry_engine/test_output" --debug
python3 -m rds_engine.export_image_asset_audit_csv --output "./output/current_audits.csv" --only-audited --limit 5

# echo "------------------------------------------------------------ spotlights ------------------------------------------------------------"
python3 -m rds_engine.init_tables init
python3 -m rds_engine.provider_spotlight





================================================ STYLE CATALOG SYNC =========================================================

python3 -m rds_engine.init_tables drop_all \
    provider_profile \
    provider_fact_record \
    provider_fact_kv \
    capsule_filter_keys \
    capsule_update_queue \
    bootstrap_url_queue \
    community_post \
    community_comment \
    weekly_squeezein_availability \
    app_user \
    app_session \
    app_user_url_profile \
    image_asset \
    image_bucket \
    image_asset_subject \
    image_asset_audit \
    image_asset_audit_kv \
    image_asset_stage_state \
    provider_spotlight_current \
    fact_key_catalog \
    provider_fact_bool_current \
    provider_fact_bool_current \
    provider_style_current \
    style_review_queue \
    provider_style_override \
    scraped_html_archive
python3 -m rds_engine.init_tables init

python3 -m rds_engine.init_tables drop_all \
    style_catalog \
    style_alias
python3 -m rds_engine.init_tables init

python3 -m rds_engine.init_tables
python3 -m tools.sync_style_catalog

python3 -m rds_engine.init_tables show style_catalog --n 50
python3 -m rds_engine.init_tables show style_alias --n 100

================================================ SMALL MACHINE =========================================================
find /home/ec2-user/.wdm/drivers/chromedriver -type f -name chromedriver

CHROMEDRIVER_PATH=/home/ec2-user/.wdm/drivers/chromedriver/linux64/142.0.7444.175/chromedriver-linux64/chromedriver \
NUM_SCRAPE_WORKERS=16 \
SERIALIZE_URL_SCRAPERS=1 \
OFFER_GATE_MAX_CONCURRENT_LLM_CALLS=2 \
CLASSIFY_MAX_CONCURRENT_LLM_CALLS=4 \
PROFILE_MAX_CONCURRENT_LLM_CALLS=2 \
OFFER_GATE_API_SLEEP=0.05 \
CLASSIFY_API_SLEEP=0.05 \
PROFILE_API_SLEEP=0.05 \
python3 -m tools.process_bootstrap_queue \
  --workers 3 \
  --url-batch-size 2 \
  --images-limit 8 \
  --image-batch-size 25 \
  --crop-mode never \
  --poll-seconds 3 \
  --bootstrap-poll-seconds 2 \
  --heartbeat-seconds 10 \
  --output "./output/test_output" \
  --recursive-images \
  --recursive-max-depth 1 \
  --recursive-max-states 40 \
  --recursive-max-workers 2 \
  --subject-workers 2 \
  --subject-lease-timeout-seconds 120 \
  --audit-workers 1 \
  --download-prefetch 2 \
  --force-mode merge

CHROMEDRIVER_PATH=/home/ec2-user/.wdm/drivers/chromedriver/linux64/142.0.7444.175/chromedriver-linux64/chromedriver \
NUM_SCRAPE_WORKERS=16 \
SERIALIZE_URL_SCRAPERS=1 \
OFFER_GATE_MAX_CONCURRENT_LLM_CALLS=4 \
CLASSIFY_MAX_CONCURRENT_LLM_CALLS=6 \
PROFILE_MAX_CONCURRENT_LLM_CALLS=3 \
OFFER_GATE_API_SLEEP=0.03 \
CLASSIFY_API_SLEEP=0.03 \
PROFILE_API_SLEEP=0.03 \
python3 -m tools.bootstrap_home_feed \
  --url "https://www.themercyseatbeauty.com/" \
  --url "https://bookthedededoll.as.me/" \
  --images-limit 8 \
  --image-batch-size 25 \
  --crop-mode never \
  --poll-seconds 2 \
  --subject-schedule round_robin \
  --subject-workers 2 \
  --subject-lease-timeout-seconds 120 \
  --audit-workers 1 \
  --download-prefetch 2 \
  --output "./output/test_output" \
  --recursive-images \
  --recursive-max-depth 1 \
  --recursive-max-states 40 \
  --recursive-max-workers 4 \
  --force-mode merge \
  --debug

CHROMEDRIVER_PATH=/home/ec2-user/.wdm/drivers/chromedriver/linux64/142.0.7444.175/chromedriver-linux64/chromedriver \
NUM_SCRAPE_WORKERS=16 \
SERIALIZE_URL_SCRAPERS=1 \
OFFER_GATE_MAX_CONCURRENT_LLM_CALLS=4 \
CLASSIFY_MAX_CONCURRENT_LLM_CALLS=6 \
PROFILE_MAX_CONCURRENT_LLM_CALLS=3 \
OFFER_GATE_API_SLEEP=0.03 \
CLASSIFY_API_SLEEP=0.03 \
PROFILE_API_SLEEP=0.03 \
python3 -m meaning_engine.cli.process_urls \
  --url "https://dayrodidit.as.me/schedule/c94e67d9" \
  --recursive-images \
  --recursive-max-depth 1 \
  --recursive-max-states 40 \
  --recursive-max-workers 4 \
  --force \
  --write-db \
  --skip-init-tables \
  --skip-local-artifacts \
  --skip-filter-key-refresh \
  --debug

python3 -m geometry_engine.cli.process_image_assets \
  --stage subject \
  --bucket-id 4b0fb82a1b8201aae3f671e58e491ceb \
  --output ./output/test_output \
  --limit 10 \
  --batch-size 5 \
  --workers 1 \
  --download-prefetch 1 \
  --schedule round_robin \
  --debug

================================================ LARGE MACHINE =========================================================

CHROMEDRIVER_PATH=/home/ec2-user/.wdm/drivers/chromedriver/linux64/142.0.7444.175/chromedriver-linux64/chromedriver \
NUM_SCRAPE_WORKERS=16 \
SERIALIZE_URL_SCRAPERS=1 \
OFFER_GATE_MAX_CONCURRENT_LLM_CALLS=8 \
CLASSIFY_MAX_CONCURRENT_LLM_CALLS=16 \
PROFILE_MAX_CONCURRENT_LLM_CALLS=6 \
OFFER_GATE_API_SLEEP=0.02 \
CLASSIFY_API_SLEEP=0.02 \
PROFILE_API_SLEEP=0.02 \
python3 -m tools.process_bootstrap_queue \
  --workers 12 \
  --url-batch-size 5 \
  --images-limit 16 \
  --image-batch-size 75 \
  --crop-mode never \
  --poll-seconds 2 \
  --bootstrap-poll-seconds 1.5 \
  --heartbeat-seconds 10 \
  --output "./output/test_output" \
  --recursive-images \
  --recursive-max-depth 1 \
  --recursive-max-states 60 \
  --recursive-max-workers 4 \
  --subject-workers 4 \
  --subject-lease-timeout-seconds 120 \
  --audit-workers 2 \
  --download-prefetch 4 \
  --force-mode merge

CHROMEDRIVER_PATH=/home/ec2-user/.wdm/drivers/chromedriver/linux64/142.0.7444.175/chromedriver-linux64/chromedriver \
NUM_SCRAPE_WORKERS=16 \
SERIALIZE_URL_SCRAPERS=1 \
OFFER_GATE_MAX_CONCURRENT_LLM_CALLS=10 \
CLASSIFY_MAX_CONCURRENT_LLM_CALLS=20 \
PROFILE_MAX_CONCURRENT_LLM_CALLS=8 \
OFFER_GATE_API_SLEEP=0.01 \
CLASSIFY_API_SLEEP=0.01 \
PROFILE_API_SLEEP=0.01 \
python3 -m tools.bootstrap_home_feed \
  --url "https://www.themercyseatbeauty.com/" \
  --url "https://bookthedededoll.as.me/" \
  --images-limit 16 \
  --image-batch-size 75 \
  --crop-mode never \
  --poll-seconds 1.5 \
  --subject-schedule round_robin \
  --subject-workers 5 \
  --subject-lease-timeout-seconds 120 \
  --audit-workers 2 \
  --download-prefetch 4 \
  --output "./output/test_output" \
  --recursive-images \
  --recursive-max-depth 1 \
  --recursive-max-states 60 \
  --recursive-max-workers 8 \
  --force-mode merge

================================================ VISUAL ONTOLOGY =========================================================

python3 -m geometry_engine.cli.process_image_assets --output "./output/test_output" --stage ontology --only-missing-current-ontology --write-db

================================================ TEST URLs =========================================================

--url "https://www.themercyseatbeauty.com/" \
--url "https://bookthedededoll.as.me/" \
--url "https://anabesthbraidin.as.me/" \
--url "https://app.acuityscheduling.com/schedule/0bc962a1" \
--url "https://app.acuityscheduling.com/schedule/35aecaa6" \
--url "https://app.acuityscheduling.com/schedule/47c8659e" \
--url "https://sweetiepies.as.me/schedule/1ee45e03" \
--url "https://roundrockafricanhairbraiding.com/services/" \
--url "https://sorabraiding.com/" \
--url "https://feminineattractions.com/pages/gallery" \
--url "https://www.braidsbyneishaa.com/mens-gallery" \
--url "https://www.eghairbraidings.com/gallery" \
--url "https://www.braidsbyneishaa.com/womens-styles" \















python3 -m rds_engine.init_tables show image_bucket --n 20
python3 -m rds_engine.init_tables show image_asset --n 5
python3 -m rds_engine.init_tables show image_asset_stage_state --n 5

python3 -m geometry_engine.cli.process_image_assets \
  --stage subject \
  --bucket-id 4b0fb82a1b8201aae3f671e58e491ceb \
  --output ./output/test_output \
  --limit 1 \
  --batch-size 1 \
  --workers 1 \
  --download-prefetch 1 \
  --schedule round_robin \
  --debug

# Also I'm not seeing anything in the "Unresolved Style Queue" in admin_style_catalog.html even after running for a given url. Why is that?







python3 -m meaning_engine.cli.process_urls \
  --url 'https://hauseofhb.as.me/schedule/3ba7f8cb' \
  --write-db \
  --force \
  --force-mode replace \
  --debug


python3 - <<'PY'
from endpoints.api.helpers import get_conn, canonicalize_provider_url

raw_url = "https://hauseofhb.as.me/schedule/3ba7f8cb"
url = canonicalize_provider_url(raw_url)
print("canonical_url:", url)

conn = get_conn()
try:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT extraction_medium, COUNT(*) AS count
            FROM provider_fact_record
            WHERE url=%s AND is_active=1
            GROUP BY extraction_medium
            ORDER BY count DESC
        """, (url,))
        for row in cur.fetchall() or []:
            print(row)

        print("\nRecent image-OCR facts:")
        cur.execute("""
            SELECT record_id, meaning_type, category, text
            FROM provider_fact_record
            WHERE url=%s
              AND is_active=1
              AND extraction_medium='website_image_ocr'
            ORDER BY record_id DESC
            LIMIT 20
        """, (url,))
        for row in cur.fetchall() or []:
            print(row)
finally:
    conn.close()
PY
