-- Parliamentary Groups Seed Data
-- Generated from current database

INSERT INTO parliamentary_groups (id, name, conference_id, url, description, is_active) VALUES
    (1, ' 日本共産党京都市会議員団', 54, 'https://cpgkyoto.jp/', NULL, true),
    (2, '公明党京都市会議員団', 54, 'https://www.komeito-kyotocity.com/#member', NULL, true),
    (3, '改新京都', 54, 'https://www2.city.kyoto.lg.jp/shikai/meibo/kaiha/kaishinkyoto.html', NULL, true),
    (4, '民主・市民フォーラム京都市会議員団', 54, 'https://www2.city.kyoto.lg.jp/shikai/meibo/kaiha/minsyu-kyoto.html', NULL, true),
    (5, '無所属', 54, 'https://www2.city.kyoto.lg.jp/shikai/meibo/kaiha/mushozoku.html', NULL, true),
    (6, '維新・京都・国民市会議員団', 54, 'https://www2.city.kyoto.lg.jp/shikai/meibo/kaiha/ishin-kyoto-kokumin.html', NULL, true),
    (7, '自由民主党京都市会議員団', 54, 'https://jimin-kyoto.jp/member_list/', NULL, true)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    conference_id = EXCLUDED.conference_id,
    url = EXCLUDED.url,
    description = EXCLUDED.description,
    is_active = EXCLUDED.is_active;

-- Reset sequence to max id + 1 (Issue #1036)
SELECT setval('parliamentary_groups_id_seq',
    COALESCE((SELECT MAX(id) FROM parliamentary_groups), 0) + 1, false);
