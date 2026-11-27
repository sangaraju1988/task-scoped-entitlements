# Under-scoping sample (E3)

Population: 361 insufficient TSE (k=1) scopes; sample: 100 (numpy seed 0).

## bird-0 (bird, moderate) -> **missing_column**
- Q: Among schools with a school-level SAT excellence rate above 0.3, what is the highest ages-5-17 free-meal eligibility rate?
- Evidence: SAT excellence rate is the share of test takers scoring at least 1500.
- Gold: `SELECT MAX(1.0 * f."Free Meal Count (Ages 5-17)" / NULLIF(f."Enrollment (Ages 5-17)", 0)) FROM frpm AS f JOIN satscores AS s ON s.cds = f.cdscode WHERE s.rtype = 'S' AND s.numtsttakr > 0 AND f."Enrollment (Ages 5-17)" > 0 AND 1.0 * s.numge1500 / NULLIF(s.numtsttakr, 0) > 0.3`
- Detail: {"missing_cols": ["satscores.rtype"]}

## bird-1 (bird, challenging) -> **missing_column**
- Q: For locally funded schools whose K-12 minus ages-5-17 enrollment difference exceeds the average such difference among locally funded schools, list each school's directory-listed name and DOC type.
- Evidence: 
- Gold: `SELECT s.school, s.doctype FROM frpm AS f JOIN schools AS s ON f.cdscode = s.cdscode WHERE s.fundingtype = 'Locally funded' AND (f."Enrollment (K-12)" - f."Enrollment (Ages 5-17)") > (SELECT AVG(f2."Enrollment (K-12)" - f2."Enrollment (Ages 5-17)") FROM frpm AS f2 JOIN schools AS s2 ON f2.cdscode = s2.cdscode WHERE s2.fundingtype = 'Locally funded') ORDER BY s.cdscode NULLS FIRST`
- Detail: {"missing_cols": ["schools.doctype", "schools.fundingtype"]}

## bird-10 (bird, challenging) -> **row_filter**
- Q: I'm profiling the High Tech High charter network in San Diego. For charter number 756, what is the average number of SAT test takers per school across all of its schools with a San Diego mailing city? Count every school regardless of operational status, and treat a school with no SAT record as having zero test takers. Round the average to two decimals.
- Evidence: Charter number 756 is the state-issued charter number.
- Gold: `SELECT ROUND(CAST(SUM(COALESCE(sc.numtsttakr, 0)) * 1.0 / NULLIF(COUNT(*), 0) AS DECIMAL), 2) AS avg_sat_test_takers_per_school FROM schools AS s LEFT JOIN satscores AS sc ON sc.cds = s.cdscode WHERE CASE WHEN (s.charternum) IS NULL THEN NULL ELSE CAST(COALESCE(SUBSTRING(CAST((s.charternum) AS TEXT) FROM '^[[:space:]]*[+-]?[0-9]+'), '0') AS BIGINT) END = 756 AND s.mailcity = 'San Diego'`
- Detail: {"predicates": {"schools": "(lower(\"charternum\"::text) = lower('756')) AND (lower(\"mailcity\"::text) = lower('San Diego'))"}, "err": ""}

## bird-101 (bird, challenging) -> **missing_column**
- Q: I'm putting together a localization report. Find the sets that belong to the same expansion type as "From the Vault: Lore" – include that set itself if it qualifies. Among those, which sets never received a name in any foreign language? For each one, give me the set's name and its release date. List each qualifying set once, from the earliest release date to the latest. Don't include anything else.
- Evidence: Expansion type means the category a set belongs to, such as core, expansion or masters.
- Gold: `SELECT s.name, s.releasedate FROM sets AS s WHERE s.type = (SELECT type FROM sets WHERE name = 'From the Vault: Lore') AND NOT EXISTS(SELECT 1 FROM set_translations AS t WHERE t.setcode = s.code AND NOT t.translation IS NULL) ORDER BY s.releasedate NULLS FIRST`
- Detail: {"missing_cols": ["set_translations.translation"]}

## bird-105 (bird, challenging) -> **missing_column**
- Q: We're planning translation work for upcoming set releases and want to know how extensively a recent release year was localized. What was the average number of languages in which sets released in 2016 had their names translated? By 'released in 2016' I mean the release date falls within calendar year 2016. Every set released in 2016 counts toward the average, including any whose names were translated into no language at all (those count as zero). A language counts for a set when the set's name is rendered in that language. Please give me just that one number, rounded to two decimals.
- Evidence: Set name translation: the set's name rendered in another language.
- Gold: `SELECT ROUND(CAST(AVG(n) AS DECIMAL), 2) AS avg_languages FROM (SELECT s.id, COUNT(DISTINCT CASE WHEN NOT st.translation IS NULL AND TRIM(CAST(st.translation AS TEXT)) <> '' THEN st.language END) AS n FROM sets AS s LEFT JOIN set_translations AS st ON s.code = st.setcode WHERE SUBSTRING(CAST(s.releasedate AS TEXT) FROM 1 FOR 4) = '2016' GROUP BY s.id) AS __photo_derived_1`
- Detail: {"missing_cols": ["sets.releasedate"]}

## bird-109 (bird, challenging) -> **missing_column**
- Q: I'm building a French-language cube and want some big finishers for it. How many different creature cards with power 10 or greater have at least one printing in a set whose name has a French translation? Please return just that single number. Note: a set qualifies based on its name having a French translation, no matter when it was released or what type of set it is, and a card counts if any of its printings comes from such a set.
- Evidence: French translation: the set's name as given in French.
- Gold: `SELECT COUNT(DISTINCT name) AS total_creature_cards FROM cards WHERE CASE WHEN (power) IS NULL THEN NULL ELSE CAST(COALESCE(SUBSTRING(CAST((power) AS TEXT) FROM '^[[:space:]]*[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?'), '0') AS DOUBLE PRECISION) END >= 10 AND CAST(types AS TEXT) LIKE '%Creature%' AND setcode IN (SELECT setcode FROM set_translations WHERE language = 'French' AND NOT tra`
- Detail: {"missing_cols": ["cards.types"]}

## bird-11 (bird, challenging) -> **missing_column**
- Q: Following up on the SAT participation review: among the currently operating high schools in the district with NCES identification number 0613360 that had no SAT test takers, which one begins serving students at the earliest grade? Please give me each such school's name and grade span served. Note that a high school must actually enroll students through grade 12-offering grade 12 without enrollment doesn't count. A school with no SAT record counts as having zero SAT test takers and should be included; only exclude schools with a positive number of SAT test takers. Compare starting grades as school grades-preschool comes before kindergarten, which comes before grade 1-and use the lowest grade the school actually serves, not just what it offers. If several schools tie at the earliest grade, list them all alphabetically by school name.
- Evidence: NCES identification number 0613360 is the school district identification number assigned by the National Center for Education Statistics.
- Gold: `WITH cohort AS (SELECT s.school AS school_name, s.gsserved AS grade_span_served, CASE WHEN SUBSTRING(CAST(s.gsserved AS TEXT) FROM 1 FOR POSITION('-' IN s.gsserved || '-') - 1) = 'P' THEN -1 WHEN SUBSTRING(CAST(s.gsserved AS TEXT) FROM 1 FOR POSITION('-' IN s.gsserved || '-') - 1) = 'K' THEN 0 ELSE CASE WHEN (SUBSTRING(CAST(s.gsserved AS TEXT) FROM 1 FOR POSITION('-' IN s.gsserved || '-') - 1)) IS`
- Detail: {"missing_cols": ["schools.statustype"]}

## bird-110 (bird, challenging) -> **missing_column**
- Q: I'm researching the Commander banned list. Can you tell me the average mana value of the creature cards that are banned in at least one play format, considering only cards ranked in EDHRec's top 1000 most popular (ranks 1 through 1000, where rank 1 is the most popular)? Give me the average as a single number rounded to one decimal place. Keep in mind that a card printed in several sets is still just one card with one EDHRec rank and one mana value.
- Evidence: EDHRec rank: a card's popularity rank on EDHRec, from 1 (most popular) to 1000.
- Gold: `SELECT ROUND(CAST(AVG(t.cmc) AS DECIMAL), 1) AS average_mana_value FROM (SELECT c.name, c.convertedmanacost AS cmc FROM cards AS c INNER JOIN legalities AS l ON l.uuid = c.uuid WHERE POSITION('Creature' IN c.types) > 0 AND c.edhrecrank BETWEEN 1 AND 1000 AND l.status = 'Banned' GROUP BY c.name, c.convertedmanacost) AS t`
- Detail: {"missing_cols": ["cards.convertedmanacost", "cards.name", "cards.types"]}

## bird-127 (bird, challenging) -> **row_filter**
- Q: I'd like to gauge the standing of our United Kingdom contributor community on the site. Can you give me the combined reputation of the users based in the United Kingdom who have posted on the site, as a single total? Please write the country by its full name, "United Kingdom", and don't substitute abbreviations. I just need the one number, not a per-user list.
- Evidence: Reputation is the score the site assigns each user. A user who has posted owns at least one item in the site's post collection.
- Gold: `SELECT SUM(u.reputation) AS combined_reputation FROM users AS u WHERE CAST(u.location AS TEXT) LIKE '%United Kingdom%' AND u.id IN (SELECT p.owneruserid FROM posts AS p WHERE NOT p.owneruserid IS NULL)`
- Detail: {"predicates": {"users": "lower(\"location\"::text) = lower('United Kingdom')"}, "err": ""}

## bird-130 (bird, challenging) -> **missing_column**
- Q: I'm putting together a report for the site owners on where people who started posting during 2010 were located, with a focus on India. Could you tell me how many of the users whose first post was created in 2010 are located in India? By 2010 I mean the calendar year 2010, and by India I mean the country itself, not any place whose name merely contains the word.
- Evidence: A user's first post is the earliest-created post among the posts that user owns.
- Gold: `WITH RECURSIVE fp AS (SELECT owneruserid AS uid, MIN(creaiondate) AS fdate FROM posts WHERE NOT owneruserid IS NULL GROUP BY owneruserid), locs AS (SELECT u.id AS uid, u.location AS loc FROM users AS u JOIN fp ON fp.uid = u.id WHERE fp.fdate >= '2010-01-01' AND fp.fdate < '2011-01-01'), parts(uid, head, tail) AS (SELECT uid, CASE WHEN POSITION(',' IN loc) > 0 THEN SUBSTRING(CAST(loc AS TEXT) FROM `
- Detail: {"missing_cols": ["posts.creaiondate"]}

## bird-135 (bird, challenging) -> **missing_column**
- Q: What is the total score of the questions tagged 'r' that link to the question titled "A Probability distribution value exceeding 1 is OK?"? I only need the total score of those linking questions.
- Evidence: 'r' here means the R programming language for statistical computing, not the letter on its own.
- Gold: `WITH target AS (SELECT id FROM posts WHERE title = 'A Probability distribution value exceeding 1 is OK?'), linkers AS (SELECT DISTINCT pl.postid AS pid FROM postlinks AS pl INNER JOIN target AS tg ON pl.relatedpostid = tg.id) SELECT SUM(p.score) AS total_score FROM linkers AS l INNER JOIN posts AS p ON p.id = l.pid WHERE EXISTS(SELECT 1 FROM tags AS t WHERE t.tagname = 'r' AND CAST(p.tags AS TEXT)`
- Detail: {"missing_cols": ["posts.tags"]}

## bird-136 (bird, challenging) -> **row_filter**
- Q: I'm profiling users by where they say they live. Among the users located in Germany, who has the second most badges of all time? By second most I mean the highest badge total strictly below the top holder's total. If several users tie at that total, include all of them. Please give me each such user's display name and their badge total, ordered by display name.
- Evidence: Badges: the badges a user has obtained, one badge award per record.
- Gold: `WITH per_user AS (SELECT u.id, u.displayname, COUNT(b.id) AS badge_count FROM users AS u LEFT JOIN badges AS b ON b.userid = u.id WHERE CAST(u.location AS TEXT) LIKE '%Germany%' GROUP BY u.id, u.displayname) SELECT displayname, badge_count FROM per_user WHERE badge_count = (SELECT MAX(badge_count) FROM per_user AS p2 WHERE p2.badge_count < (SELECT MAX(badge_count) FROM per_user)) ORDER BY displayn`
- Detail: {"predicates": {"users": "lower(\"location\"::text) = lower('Germany')"}, "err": ""}

## bird-139 (bird, challenging) -> **row_filter**
- Q: I'm preparing a report on international participation. How many users located in India had earned a Yearling badge before 2014? 'Before 2014' should mean before 1 January 2014. I just need the single count, nothing else.
- Evidence: 'Yearling' is a badge a member earns for a year of activity on the site.
- Gold: `SELECT COUNT(DISTINCT t1.userid) AS user_count FROM badges AS t1 INNER JOIN users AS t2 ON t1.userid = t2.id WHERE CAST(t2.location AS TEXT) LIKE '%India%' AND t1.name = 'Yearling' AND t1.date < '2014-01-01'`
- Detail: {"predicates": {"badges": "lower(\"name\"::text) = lower('Yearling')", "users": "lower(\"location\"::text) = lower('India')"}, "err": ""}

## bird-144 (bird, challenging) -> **row_filter**
- Q: What was the average reputation of users located in India who created a post in 2010? Please give me a single number rounded to two decimal places. Note: 'in 2010' means the calendar year 2010 based on the post's creation date, and any type of post counts. A user counts as located in India only if their location is actually India - a place that merely contains the word India (like the US state Indiana) doesn't count.
- Evidence: 
- Gold: `SELECT ROUND(CAST(AVG(u.reputation) AS DECIMAL), 2) AS avg_reputation FROM users AS u WHERE (TRIM(CAST(u.location AS TEXT)) = 'India' OR (POSITION(',' IN u.location) > 0 AND TRIM(CAST(SUBSTRING(CAST(u.location AS TEXT) FROM POSITION(',' IN u.location) + 1) AS TEXT)) = 'India')) AND u.id IN (SELECT p.owneruserid FROM posts AS p WHERE p.creaiondate >= '2010-01-01' AND p.creaiondate < '2011-01-01')`
- Detail: {"predicates": {"users": "lower(\"location\"::text) = lower('India')"}, "err": ""}

## bird-159 (bird, challenging) -> **missing_column**
- Q: I'm reviewing customer 15621's fuel spending on the fleet card in 2013. What was their average fuel consumption per month, counting only the months in which they actually purchased fuel? Give me the single average value rounded to two decimal places.
- Evidence: 
- Gold: `SELECT ROUND(CAST(SUM(consumption) / NULLIF(COUNT(*), 0) AS DECIMAL), 2) AS average_monthly_consumption FROM yearmonth WHERE customerid = 15621 AND date BETWEEN '201301' AND '201312' AND consumption > 0`
- Detail: {"missing_cols": ["yearmonth.date"]}

## bird-169 (bird, challenging) -> **missing_column**
- Q: By what percentage is Ariel Borysiuk's overall rating in his latest attribute record higher than Paulin Puel's latest overall rating? Round to two decimals.
- Evidence: 
- Gold: `WITH latest AS (SELECT p.player_name, a.overall_rating, ROW_NUMBER() OVER (PARTITION BY p.player_api_id ORDER BY a.date DESC NULLS LAST, a.id DESC NULLS LAST) AS rn FROM player AS p JOIN player_attributes AS a ON a.player_api_id = p.player_api_id WHERE p.player_name IN ('Ariel Borysiuk', 'Paulin Puel')) SELECT ROUND(CAST(100.0 * (MAX(CASE WHEN player_name = 'Ariel Borysiuk' THEN overall_rating END`
- Detail: {"missing_cols": ["player_attributes.date"]}

## bird-175 (bird, challenging) -> **missing_column**
- Q: What is the average height in centimeters of players whose current defensive work rate grade is not medium? Use each player's most recent rating record to determine their current grade, and round the result to two decimal places. I just need that single number.
- Evidence: Defensive work rate grades run low, medium and high.
- Gold: `WITH latest AS (SELECT player_api_id, defensive_work_rate, ROW_NUMBER() OVER (PARTITION BY player_api_id ORDER BY date DESC NULLS LAST, id DESC NULLS LAST) AS rn FROM player_attributes) SELECT ROUND(CAST(AVG(p.height) AS DECIMAL), 2) AS average_height FROM latest AS l JOIN player AS p ON p.player_api_id = l.player_api_id WHERE l.rn = 1 AND l.defensive_work_rate IN ('low', 'high')`
- Detail: {"missing_cols": ["player_attributes.date"]}

## bird-180 (bird, challenging) -> **missing_column**
- Q: What was the build-up play dribbling class for the team from England with short name POR on 10 September 2015? I just need that single class value for that team on that calendar day.
- Evidence: 
- Gold: `SELECT t2.buildupplaydribblingclass FROM team AS t1 INNER JOIN team_attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_short_name = 'POR' AND t1.team_api_id IN (SELECT m.home_team_api_id FROM match AS m INNER JOIN country AS c ON c.id = m.country_id WHERE c.name = 'England' UNION SELECT m.away_team_api_id FROM match AS m INNER JOIN country AS c ON c.id = m.country_id WHERE c.name = `
- Detail: {"missing_cols": ["team_attributes.date"]}

## bird-210 (bird, challenging) -> **missing_column**
- Q: I'm preparing for a client review and want to gauge how indebted our older customers' accounts are, including accounts that never took any loans. Could you give me the average number of loans per account among accounts whose owner was born before 1950? By 'born before 1950' I mean a birth date earlier than 1 January 1950, and all loans should count regardless of when they were approved. Please give me the average rounded to two decimal places, and nothing else.
- Evidence: The owner of an account is the client with the OWNER disposition; a DISPONENT is a co-holder who does not own it. A loan is a credit granted on the account, recorded with the date it was approved.
- Gold: `WITH owner AS (SELECT t2.account_id, t1.birth_date FROM client AS t1 INNER JOIN disp AS t2 ON t1.client_id = t2.client_id WHERE t2.type = 'OWNER') SELECT ROUND(CAST(CASE WHEN (COUNT(t3.loan_id)) IS NULL THEN NULL ELSE CAST(COALESCE(SUBSTRING(CAST((COUNT(t3.loan_id)) AS TEXT) FROM '^[[:space:]]*[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?'), '0') AS DOUBLE PRECISION) END / NULLIF(COUNT(DIS`
- Detail: {"missing_cols": ["disp.type"]}

## bird-22 (bird, challenging) -> **missing_column**
- Q: I have a school's CDS code from a separate list of Alameda County schools on Breakfast Provision 2, and I need to confirm which school it is. For the school with CDS code 1612590136051, please give me the school name and the educational instruction level name. This CDS code identifies exactly one school, so return only that school.
- Evidence: Breakfast Provision 2: the NSLP provision status category the school participates in. CDS code 1612590136051: the school identifier being asked about.
- Gold: `SELECT s.school, s.eilname FROM schools AS s INNER JOIN frpm AS f ON s.cdscode = f.cdscode WHERE f."NSLP Provision Status" = 'Breakfast Provision 2' AND f."County Name" = 'Alameda' AND CASE WHEN (s.cdscode) IS NULL THEN NULL ELSE CAST(COALESCE(SUBSTRING(CAST((s.cdscode) AS TEXT) FROM '^[[:space:]]*[+-]?[0-9]+'), '0') AS BIGINT) END = 1612590136051`
- Detail: {"missing_cols": ["schools.eilname"]}

## bird-220 (bird, challenging) -> **missing_column**
- Q: I want to check whether our biggest short-term loans cluster in populous branch districts and how well-off those areas are. Looking at 24-month loans on accounts with weekly statement issuance, take the ten largest loans ranked by approved amount from highest to lowest — if two loans have the same amount, the one with the smaller loan id ranks first, and ranking continues consecutively after a tie. The district of a loan is the district where the branch managing the loan account is located. Among the districts those ten loans come from, I need: the district with the most inhabitants (if two districts tie on inhabitants, the one with the smaller district id counts as more populous), that district's number of inhabitants, and the average salary across those districts rounded to two decimals.
- Evidence: Weekly statement issuance means account issuance frequency 'POPLATEK TYDNE'. A district's inhabitants are its number of inhabitants, and its average salary is its average yearly salary.
- Gold: `WITH ranked AS (SELECT l.loan_id, a.district_id, ROW_NUMBER() OVER (ORDER BY l.amount DESC NULLS LAST, l.loan_id ASC NULLS FIRST) AS rn FROM loan AS l JOIN account AS a ON a.account_id = l.account_id WHERE l.duration = 24 AND a.frequency = 'POPLATEK TYDNE'), top10 AS (SELECT * FROM ranked WHERE rn <= 10), districts AS (SELECT d.district_id, d.a2 AS district_name, CASE WHEN (d.a4) IS NULL THEN NULL`
- Detail: {"missing_cols": ["district.a2"]}

## bird-222 (bird, challenging) -> **row_filter**
- Q: I'm preparing a client review for client 3541. For each account this client can access, I need one row with: the account id, the date the account was opened, its frequency, the name and region of the district where the account is held, whether that district is the client's home district (Yes/No), that district's average salary, the loan repayment status (none if there's no loan), the loan amount (0 if no loan), the number of transactions over the account's whole recorded history, total income, total expense, net balance, the number of clients whose home district lies in that region, the name of the most populous district in that region, that district's number of inhabitants, and the account district's population rank within its region. Order the rows by number of transactions, most first, with ties broken by ascending account id. The client's home district is the district recorded for the client, and population means number of inhabitants. For ranks, the most populous district is rank 1; districts with equal population share a rank and the next rank skips.
- Evidence: PRIJEM = incoming transaction; VYDAJ = outgoing transaction; net balance = total income - total expense
- Gold: `WITH acct AS (SELECT d.account_id, a.date AS opened, a.frequency AS freq, a.district_id AS branch_district, c.district_id AS home_district FROM client AS c JOIN disp AS d ON d.client_id = c.client_id JOIN account AS a ON a.account_id = d.account_id WHERE c.client_id = 3541), stats AS (SELECT ac.account_id, ac.opened, ac.freq, ac.branch_district, ac.home_district, COUNT(t.trans_id) AS transaction_c`
- Detail: {"predicates": {"client": "\"client_id\" = 3541"}, "err": ""}

## bird-224 (bird, challenging) -> **missing_column**
- Q: For a regional risk review, I need to look at our largest 24-month loans. Please find the ten loans with the largest approved amount among loans with a 24-month duration on accounts that have weekly statement issuance. For each of these ten loans, give me: the district of the branch servicing the account, the approved amount, the approval date, and the account balance at the end of the day the loan was approved. Two rules: if two loans have the same approved amount, the one approved earlier counts as larger; and if several transactions share that last day, the one with the higher transaction id counts as the later one. List the results from the largest approved amount down.
- Evidence: Weekly statement issuance means statement frequency is 'POPLATEK TYDNE'; loan duration is stated in months.
- Gold: `WITH top_loans AS (SELECT l.loan_id, l.account_id, l.amount, l.date AS loan_date, d.a2 AS district_name FROM loan AS l JOIN account AS a ON a.account_id = l.account_id JOIN district AS d ON d.district_id = a.district_id WHERE l.duration = 24 AND a.frequency = 'POPLATEK TYDNE' ORDER BY l.amount DESC NULLS LAST, l.date ASC NULLS FIRST, l.loan_id ASC NULLS FIRST LIMIT 10) SELECT district_name, amount`
- Detail: {"missing_cols": ["district.a2"]}

## bird-230 (bird, challenging) -> **missing_column**
- Q: I need to profile our three largest loans held by female clients. Please report for each of these loans: the client id, loan amount, duration in months, total payments, interest paid, loan status, the district and region of the branch where the loan's account is held, the account's transaction count and total deposits, an income category, the number of loans the bank has granted in that region, the average of the average salaries of that region's districts, and the client's completed age on 2026-10-09. A few notes: the three largest loans are the three highest approved loan amounts, and if amounts tie, include all tied loans. Total payments is the monthly payment times the duration, and interest paid is total payments minus the approved amount; round money figures to two decimals. The income category is High Income if total deposits exceed twice the loan amount, Medium Income if they exceed the loan amount, and Low Income otherwise. Loans in a region counts every loan the bank has granted in that region for all clients, not only female clients. The region's average salary is the average of the average salaries of the districts in that region, rounded to two decimals. For the age, use the completed age on 2026-10-09, subtracting one if the birthday hasn't occurred by that date.
- Evidence: Female means client gender = 'F'. Deposits are transactions recorded as PRIJEM (credits to the account). District average salary is the district's average salary figure.
- Gold: `WITH female_loans AS (SELECT c.client_id, c.birth_date, d.account_id, l.loan_id, l.amount, l.duration, l.payments, l.status, a.district_id, RANK() OVER (ORDER BY l.amount DESC NULLS LAST) AS rnk FROM client AS c JOIN disp AS d ON c.client_id = d.client_id AND d.type = 'OWNER' JOIN loan AS l ON d.account_id = l.account_id JOIN account AS a ON l.account_id = a.account_id WHERE c.gender = 'F'), regio`
- Detail: {"missing_cols": ["disp.type", "trans.type"]}

## bird-232 (bird, challenging) -> **missing_column**
- Q: I'm putting together a market-coverage report on how our 1997 rollout of monthly-statement accounts reached large urban districts. For districts with at least 100,000 inhabitants that had at least one monthly-statement account opened during calendar year 1997, please give me: the total number of monthly-statement accounts opened in those districts during 1997, how many districts are involved, and the average salary across these qualifying districts rounded to two decimals.
- Evidence: Monthly statement issuance means the account's statement frequency is 'POPLATEK MESICNE'.
- Gold: `WITH qualifying_districts AS (SELECT d.district_id, d.a11 FROM district AS d WHERE CASE WHEN (d.a4) IS NULL THEN NULL ELSE CAST(COALESCE(SUBSTRING(CAST((d.a4) AS TEXT) FROM '^[[:space:]]*[+-]?[0-9]+'), '0') AS BIGINT) END >= 100000 AND EXISTS(SELECT 1 FROM account AS a WHERE a.district_id = d.district_id AND a.frequency = 'POPLATEK MESICNE' AND a.date BETWEEN '1997-01-01' AND '1997-12-31')) SELECT`
- Detail: {"missing_cols": ["account.date", "district.a4"]}

## bird-241 (bird, challenging) -> **missing_table**
- Q: What percentage of Lewis Hamilton's recorded race entries from 2010 onward were not victories? Round to two decimals.
- Evidence: 
- Gold: `SELECT ROUND(CAST(100.0 * SUM(CASE WHEN x.positionorder <> 1 THEN 1 ELSE 0 END) / NULLIF(NULLIF(COUNT(*), 0), 0) AS DECIMAL), 2) FROM results AS x JOIN drivers AS d ON d.driverid = x.driverid JOIN races AS r ON r.raceid = x.raceid WHERE d.forename = 'Lewis' AND d.surname = 'Hamilton' AND r.year >= 2010`
- Detail: {"missing_tables": ["races"], "missing_cols": ["results.positionorder"]}

## bird-251 (bird, challenging) -> **missing_column**
- Q: I'm comparing pit stop activity at the newer Grand Prix weekends. Among the 2017 races that were not hosted in 2000, what was the average number of pit stops per race? Please take the average of all of those races and round it to two decimal places.
- Evidence: Hosted in 2000 means the race was on the 2000 race calendar.
- Gold: `WITH cohort AS (SELECT raceid FROM races WHERE year = 2017 AND NOT name IN (SELECT name FROM races WHERE year = 2000)) SELECT ROUND(CAST(1.0 * (SELECT COUNT(*) FROM pitstops WHERE raceid IN (SELECT raceid FROM cohort)) / NULLIF((SELECT COUNT(*) FROM cohort), 0) AS DECIMAL), 2) AS avg_pit_stops_per_race`
- Detail: {"missing_cols": ["races.name"]}

## bird-267 (bird, challenging) -> **missing_table**
- Q: For every edition of the French Grand Prix from the 1990 season through the most recent edition, I'd like to know which drivers set a fastest lap of the race slower than 90 seconds. For each such driver, give me the date of the edition, the driver's forename and surname, and their fastest lap time of that race in m:ss.mmm form. If several drivers in an edition clear that 90-second mark, list one row per driver. If an edition has no driver over 90 seconds, still show the edition with its date, but no driver or lap time. Please order the rows from the earliest edition date to the latest, and within an edition by driver surname alphabetically - if two drivers share the same fastest-lap time, order them by forename alphabetically.
- Evidence: A driver's fastest lap in an edition means the shortest time they took to complete any single lap of that race, measured from the start of that lap; the 90-second threshold applies to that fastest lap, not to an average.
- Gold: `WITH editions AS (SELECT raceid, date FROM races WHERE name = 'French Grand Prix' AND year >= 1990), best AS (SELECT raceid, driverid, MIN(milliseconds) AS best FROM laptimes GROUP BY raceid, driverid) SELECT e.date, d.forename, d.surname, lt.time FROM editions AS e LEFT JOIN best AS b ON b.raceid = e.raceid AND b.best > 90 * 1000 LEFT JOIN laptimes AS lt ON lt.raceid = b.raceid AND lt.driverid = `
- Detail: {"missing_tables": ["laptimes"], "missing_cols": []}

## bird-269 (bird, challenging) -> **missing_column**
- Q: I'm writing a piece on the new generation of British Formula 1 talent. Among British F1 drivers born after 1980, who set the fastest Q3 qualifying time, what was that time, and at which race and in which year was it set? Please give me the driver's full name, the race name, the race year, and the Q3 time. By 'born after 1980' I mean the year of birth is later than 1980. If two qualifying results tie for the fastest Q3 time, I'd like a row for each.
- Evidence: Q3 is the final part of the qualifying session that decides the front of the starting grid.
- Gold: `WITH cohort AS (SELECT q.driverid, q.raceid, q.q3 FROM drivers AS d JOIN qualifying AS q ON d.driverid = q.driverid WHERE d.nationality = 'British' AND CASE WHEN (EXTRACT(YEAR FROM CAST(d.dob AS TIMESTAMP))) IS NULL THEN NULL ELSE CAST(COALESCE(SUBSTRING(CAST((EXTRACT(YEAR FROM CAST(d.dob AS TIMESTAMP))) AS TEXT) FROM '^[[:space:]]*[+-]?[0-9]+'), '0') AS BIGINT) END > 1980 AND NOT q.q3 IS NULL AND`
- Detail: {"missing_cols": ["drivers.dob"]}

## bird-273 (bird, challenging) -> **missing_column**
- Q: I'm writing a piece about how the same common forenames recur across Formula 1 history. Could you tell me how many different drivers named Peter have ever won a Formula 1 race, and the same for drivers named John? Please give me one count per forename, so I can compare the two — if they turn out to be equal, just report both counts side by side. Nothing else needed.
- Evidence: A race win means the driver finished first in that race.
- Gold: `SELECT t1.forename, COUNT(DISTINCT t1.driverid) AS winner_drivers FROM drivers AS t1 INNER JOIN results AS t2 ON t2.driverid = t1.driverid WHERE t2.positionorder = 1 AND t1.forename IN ('John', 'Peter') GROUP BY t1.forename ORDER BY t1.forename NULLS FIRST`
- Detail: {"missing_cols": ["results.positionorder"]}

## bird-278 (bird, challenging) -> **missing_column**
- Q: For my monthly recap I need the fastest pit stop made during any F1 race held in September 2016. Please tell me the driver's full name, the pit stop time, the name of the race where it happened, the circuit name, and the circuit location. If two or more pit stops share the fastest time, list each of them with its own driver, race, circuit name and circuit location.
- Evidence: By pit stop time I mean the elapsed time of a pit stop, from the car arriving at its pit to rejoining the race.
- Gold: `WITH scope AS (SELECT ps.driverid, ps.duration, ps.milliseconds, r.raceid FROM pitstops AS ps JOIN races AS r ON r.raceid = ps.raceid WHERE r.date >= '2016-09-01' AND r.date < '2016-10-01') SELECT d.forename || ' ' || d.surname AS driver_name, s.duration AS pit_stop_time, r.name AS race_name, c.name AS circuit_name, c.location AS circuit_location FROM scope AS s JOIN drivers AS d ON d.driverid = s`
- Detail: {"missing_cols": ["pitstops.duration", "pitstops.milliseconds", "races.date"]}

## bird-286 (bird, challenging) -> **missing_column**
- Q: Which Chinese Grand Prix edition from the 2000s (2000–2009 seasons) had the earliest scheduled local start time? Give me the season year of that edition and the runner-up's time gap to the winner (the runner-up being the driver classified second at the finish). If several editions share the earliest scheduled local start time, use the most recent one.
- Evidence: Scheduled local start time: the time of day the race was scheduled to start, local to the circuit.
- Gold: `SELECT r.year, res.time AS runner_up_gap FROM races AS r JOIN results AS res ON res.raceid = r.raceid WHERE r.name = 'Chinese Grand Prix' AND r.year BETWEEN 2000 AND 2009 AND res.positionorder = 2 AND NOT r.time IS NULL AND r.time = (SELECT MIN(r2.time) FROM races AS r2 WHERE r2.name = 'Chinese Grand Prix' AND r2.year BETWEEN 2000 AND 2009 AND NOT r2.time IS NULL) ORDER BY r.year DESC NULLS LAST L`
- Detail: {"missing_cols": ["results.positionorder"]}

## bird-288 (bird, challenging) -> **missing_column**
- Q: I'm writing about how the Canadian Grand Prix moved to early-evening starts. Could you find the editions of the Canadian Grand Prix from 2007 through 2017 (both years included) that began at 17:00 local time or earlier - a race that began exactly at 17:00 counts. For each one, give me the race year, the winner's forename, the winner's surname, and the winner's finish time. The winner is the single driver classified first at the finish. Nothing else, please.
- Evidence: An edition is one running of the Canadian Grand Prix in a given year; local start time is the clock time of day, local to the circuit, at which the race began, on the 24-hour clock.
- Gold: `SELECT r.year, d.forename, d.surname, res.time AS finish_time FROM races AS r JOIN results AS res ON res.raceid = r.raceid AND res.positionorder = 1 JOIN drivers AS d ON d.driverid = res.driverid WHERE r.name = 'Canadian Grand Prix' AND r.year BETWEEN 2007 AND 2017 AND CAST(r.time AS TIME) <= TIME '17:00' ORDER BY r.year NULLS FIRST`
- Detail: {"missing_cols": ["results.positionorder"]}

## bird-289 (bird, challenging) -> **missing_table**
- Q: I'm writing a retrospective on the 2017 Italian Grand Prix at Monza. For the Q3 session of that race's qualifying, can you give me the permanent career race number and surname of every driver whose Q3 lap time was strictly faster than 1 minute 38.000 seconds? I want all drivers under that mark, not just the fastest, and no particular order. Note that by permanent career race number I mean the number a driver carries throughout his career, not a one-off entry number for that weekend.
- Evidence: Q3 is the third and final qualifying session; a driver only has a Q3 time if he actually took part in that session.
- Gold: `WITH mark(t) AS (SELECT '1' || ':' || '38.000') SELECT d.number, d.surname FROM qualifying AS q INNER JOIN races AS r ON r.raceid = q.raceid INNER JOIN drivers AS d ON d.driverid = q.driverid WHERE r.year = 2017 AND r.name = 'Italian Grand Prix' AND CAST(q.q3 AS TEXT) LIKE '%:%' AND q.q3 < (SELECT t FROM mark) ORDER BY d.number NULLS FIRST`
- Detail: {"missing_tables": ["races"], "missing_cols": []}

## bird-291 (bird, challenging) -> **missing_column**
- Q: I'm looking into fastest race laps recorded by drivers born in the 1980s. Can you tell me which three drivers born between 1980 and 1990 reached the highest single fastest-lap speed at any point in their career? I'd like their first and last names, ranked from the highest career-high speed down, and if two drivers are tied on that speed, list the one born earlier first, and then the one whose last name comes first alphabetically. Please give me just the three names, nothing else.
- Evidence: Fastest lap speed: the average speed, in km/h, that a driver recorded on their single fastest lap of a race. A driver's career-high speed is based on that one lap, not an average across their laps.
- Gold: `SELECT d.forename, d.surname FROM drivers AS d JOIN results AS r ON r.driverid = d.driverid WHERE SUBSTRING(CAST(d.dob AS TEXT) FROM 1 FOR 4) BETWEEN '1980' AND '1990' AND NOT r.fastestlapspeed IS NULL GROUP BY d.driverid, d.forename, d.surname, d.dob ORDER BY MAX(CASE WHEN (r.fastestlapspeed) IS NULL THEN NULL ELSE CAST(COALESCE(SUBSTRING(CAST((r.fastestlapspeed) AS TEXT) FROM '^[[:space:]]*[+-]?`
- Detail: {"missing_cols": ["drivers.dob"]}

## bird-297 (bird, simple) -> **missing_column**
- Q: What note was recorded for the fundraising proceeds received on September 14, 2019?
- Evidence: 
- Gold: `SELECT notes FROM income WHERE source = 'Fundraising' AND date_received = '2019-09-14'`
- Detail: {"missing_cols": ["income.source"]}

## bird-298 (bird, challenging) -> **missing_column**
- Q: What is the ratio of the Advertisement budget for the Yearly Kickoff meeting to that for the October Meeting?
- Evidence: 
- Gold: `SELECT CASE WHEN (SUM(CASE WHEN t2.event_name = 'Yearly Kickoff' THEN t1.amount ELSE 0 END)) IS NULL THEN NULL ELSE CAST(COALESCE(SUBSTRING(CAST((SUM(CASE WHEN t2.event_name = 'Yearly Kickoff' THEN t1.amount ELSE 0 END)) AS TEXT) FROM '^[[:space:]]*[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?'), '0') AS DOUBLE PRECISION) END / NULLIF(SUM(CASE WHEN t2.event_name = 'October Meeting' THEN t1`
- Detail: {"missing_cols": ["budget.category", "event.type"]}

## bird-309 (bird, challenging) -> **row_filter**
- Q: For our end-of-year report, I need one figure: the average number of members who attended each event that carried a budget line for advertising, covering every such event across the club's records regardless of when it took place. Please give it as a single number rounded to two decimal places.
- Evidence: A budget line for advertising means a budget entry whose category is advertising.
- Gold: `WITH att AS (SELECT link_to_event, COUNT(DISTINCT link_to_member) AS members FROM attendance GROUP BY link_to_event) SELECT ROUND(CAST(AVG(COALESCE(att.members, 0)) AS DECIMAL), 2) AS average_attendance FROM event AS t1 INNER JOIN budget AS t2 ON t2.link_to_event = t1.event_id AND t2.category = 'Advertisement' LEFT JOIN att ON att.link_to_event = t1.event_id`
- Detail: {"predicates": {"budget": "lower(\"category\"::text) = lower('advertising')"}, "err": ""}

## bird-314 (bird, challenging) -> **missing_table**
- Q: I'm finalizing the semester wrap-up report and need one number: how many different kinds of things the club bought for events that went over budget this semester. A few things to keep in mind: an event counts as over budget if, in at least one of its budgeted categories, we spent more than we budgeted for that category - the budgeted amount minus what was actually spent came out below zero. Also, a single purchase can cover several kinds of things at once, and the purchase description lists what it bought, so make sure each kind is counted. The answer should cover the whole semester shown in the records, and I just need the single integer count, nothing else.
- Evidence: went over budget: a budgeted category of the event ended with more spent than was budgeted for it, i.e. the amount budgeted minus the amount spent is below zero; kind of thing: a type of item bought, like water, pizza or posters
- Gold: `WITH RECURSIVE over_budget_events AS (SELECT DISTINCT link_to_event FROM budget WHERE amount - spent < 0), purchases AS (SELECT ex.expense_description AS d FROM expense AS ex JOIN budget AS b ON ex.link_to_budget = b.budget_id WHERE b.link_to_event IN (SELECT link_to_event FROM over_budget_events)), items(item, rest) AS (SELECT TRIM(CAST(SUBSTRING(CAST(d || ',' AS TEXT) FROM 1 FOR POSITION(',' IN `
- Detail: {"missing_tables": ["expense"], "missing_cols": []}

## bird-317 (bird, challenging) -> **missing_table**
- Q: For our snack budget planning: among the events that spent money on chips, which event has the highest budget amount? By budget amount I mean a single budget line, not a total across lines - compare events by their largest single budgeted line. If several events tie on that largest line, list all of their names. Please just give me the event name(s).
- Evidence: 
- Gold: `WITH chip_events AS (SELECT DISTINCT b.link_to_event AS event_id FROM budget AS b INNER JOIN expense AS x ON x.link_to_budget = b.budget_id WHERE CAST(x.expense_description AS TEXT) LIKE '%chips%') SELECT e.event_name FROM event AS e INNER JOIN budget AS b ON b.link_to_event = e.event_id WHERE e.event_id IN (SELECT event_id FROM chip_events) AND b.amount = (SELECT MAX(amount) FROM budget WHERE lin`
- Detail: {"missing_tables": ["expense"], "missing_cols": []}

## bird-330 (bird, challenging) -> **missing_column**
- Q: I'm putting together the end-of-term spending review. Who bought the most different kinds of items in October or November 2019? Please give me that member's full name, how many different kinds of items they bought in those two months, and their total spending in dollars over the same period. If two members tie for the most kinds, list every tied member with their kind count and spending.
- Evidence: An item is one of the individual things a purchase covered, such as a pizza or a bottle of water.
- Gold: `WITH RECURSIVE split AS (SELECT link_to_member, expense_description AS rest FROM expense WHERE expense_date BETWEEN '2019-10-01' AND '2019-11-30' UNION ALL SELECT link_to_member, SUBSTRING(CAST(rest AS TEXT) FROM POSITION(',' IN rest || ',') + 1) FROM split WHERE rest <> ''), items AS (SELECT link_to_member, TRIM(CAST(SUBSTRING(CAST(rest AS TEXT) FROM 1 FOR POSITION(',' IN rest || ',') - 1) AS TEX`
- Detail: {"missing_cols": ["expense.cost", "expense.expense_date", "expense.expense_description"]}

## bird-335 (bird, challenging) -> **row_filter**
- Q: Between Marvel Comics and DC Comics, which publisher has more superheroes, and by how many?
- Evidence: 
- Gold: `WITH counts AS (SELECT SUM(CASE WHEN p.publisher_name = 'Marvel Comics' THEN 1 ELSE 0 END) AS marvel_count, SUM(CASE WHEN p.publisher_name = 'DC Comics' THEN 1 ELSE 0 END) AS dc_count FROM superhero AS s JOIN publisher AS p ON p.id = s.publisher_id) SELECT CASE WHEN marvel_count > dc_count THEN 'Marvel Comics' WHEN dc_count > marvel_count THEN 'DC Comics' ELSE 'Tie' END, ABS(marvel_count - dc_coun`
- Detail: {"predicates": {"publisher": "(lower(\"publisher_name\"::text) = lower('Marvel Comics')) AND (lower(\"publisher_name\"::text) = lower('DC Comics'))"}, "err": ""}

## bird-350 (bird, challenging) -> **missing_column**
- Q: I'm putting together a comparison of the heaviest brick-strength characters. What is the average weight, in kilograms, of all superheroes whose Strength score equals the Hulk's? I just need a single integer rounded to the nearest kilogram. Include every superhero in the database, no restrictions on publisher or alignment. If a hero's weight is unknown, leave them out and average only over the heroes whose weight has actually been measured.
- Evidence: Strength is one of the six measured hero attributes, each scored on a 1-100 scale; the Hulk is the superhero named 'Hulk'; weight is the superhero's weight in kilograms.
- Gold: `SELECT CASE WHEN (ROUND(AVG(s.weight_kg))) IS NULL THEN NULL ELSE CAST(COALESCE(SUBSTRING(CAST((ROUND(AVG(s.weight_kg))) AS TEXT) FROM '^[[:space:]]*[+-]?[0-9]+'), '0') AS BIGINT) END AS average_weight_kg FROM superhero AS s INNER JOIN hero_attribute AS ha ON ha.hero_id = s.id INNER JOIN attribute AS a ON a.id = ha.attribute_id WHERE a.attribute_name = 'Strength' AND ha.attribute_value = (SELECT h`
- Detail: {"missing_cols": ["attribute.attribute_name"]}

## bird-361 (bird, challenging) -> **missing_column**
- Q: How many heroes published by Blackwulf's publisher have an eye colour that at least one hero from a different publisher also has? By "that publisher's heroes" I mean all of its heroes, not just Blackwulf. A different publisher means any other publisher, and heroes with no publisher listed shouldn't count as coming from a different publisher. I just want that single count back.
- Evidence: Eye colour: the colour of a hero's eyes as catalogued for that hero.
- Gold: `WITH blk AS (SELECT publisher_id AS pid FROM superhero WHERE superhero_name = 'Blackwulf') SELECT COUNT(*) AS hero_count FROM superhero AS m WHERE m.publisher_id = (SELECT pid FROM blk) AND m.eye_colour_id IN (SELECT d.eye_colour_id FROM superhero AS d WHERE NOT d.publisher_id IS NULL AND d.publisher_id <> (SELECT pid FROM blk))`
- Detail: {"missing_cols": ["superhero.superhero_name"]}

## bird-368 (bird, challenging) -> **row_filter**
- Q: I'd like to know how tall the heroes are who share at least one superpower with 3-D Man. Can you give me the average height in centimetres of those heroes, rounded to one decimal place? Please leave 3-D Man himself out of it, and don't count heroes whose height isn't known.
- Evidence: 
- Gold: `SELECT ROUND(CAST(AVG(s.height_cm) AS DECIMAL), 1) AS avg_height_cm FROM superhero AS s WHERE s.height_cm > 0 AND s.id <> (SELECT id FROM superhero WHERE superhero_name = '3-D Man') AND s.id IN (SELECT hp2.hero_id FROM hero_power AS hp2 WHERE hp2.power_id IN (SELECT power_id FROM hero_power WHERE hero_id = (SELECT id FROM superhero WHERE superhero_name = '3-D Man')))`
- Detail: {"predicates": {"superhero": "lower(\"superhero_name\"::text) = lower('3-D Man')"}, "err": ""}

## bird-369 (bird, challenging) -> **missing_table**
- Q: I'm writing an article about green-skinned flying villains and need a body-statistics fact. What is the average weight, in kilograms, of all green-skinned villains who can fly? By villain I mean a character whose moral affiliation is Bad. Please include only characters whose weight was actually measured-any character whose weight was never measured should be left out of the average. Give me just the single number, rounded to the nearest kilogram.
- Evidence: Flight: the power to fly.
- Gold: `SELECT ROUND(AVG(CASE WHEN s.weight_kg > 0 THEN s.weight_kg END)) AS average_weight_kg FROM superhero AS s INNER JOIN alignment AS a ON s.alignment_id = a.id INNER JOIN colour AS c ON s.skin_colour_id = c.id INNER JOIN hero_power AS hp ON hp.hero_id = s.id INNER JOIN superpower AS sp ON sp.id = hp.power_id WHERE a.alignment = 'Bad' AND c.colour = 'Green' AND sp.power_name = 'Flight'`
- Detail: {"missing_tables": ["colour"], "missing_cols": ["alignment.alignment"]}

## bird-37 (bird, challenging) -> **missing_column**
- Q: Could you pull a full profile for the school with CDS code 7618040113118? I need its name, phone number, website, average SAT reading, math and writing scores, whether it is a charter school, its K-12 enrollment for the 2014-2015 academic year, and the percentage of its students eligible for free or reduced price meals on a 0-100 scale rounded to two decimal places. Alongside that, please find the highest average SAT math score achieved by any active school with at least 10 SAT test takers – if several schools tie for the highest, just give me that single score – and how far below that highest score this school's math score falls.
- Evidence: CDS code is the California Department of Education's school identifier; a charter school is one with charter status recorded as 1.
- Gold: `WITH benchmark AS (SELECT MAX(t.avgscrmath) AS topmath FROM satscores AS t INNER JOIN schools AS s ON s.cdscode = t.cds WHERE s.statustype = 'Active' AND t.numtsttakr >= 10) SELECT s.school AS "School Name", s.phone AS "Phone Number", s.website AS website, t.avgscrread AS "Average SAT Reading Score", t.avgscrmath AS "Average SAT Math Score", t.avgscrwrite AS "Average SAT Writing Score", f."Charter`
- Detail: {"missing_cols": ["schools.statustype"]}

## bird-371 (bird, challenging) -> **missing_table**
- Q: For the article I'm writing on heroic female characters, I'd like a physique stat for the trivia box: what is the average weight in kilograms of female superheroes whose alignment is good? Only count superheroes whose weight is known. Please round the result to two decimal places.
- Evidence: Alignment: the superhero's moral category, e.g. good, bad, neutral.
- Gold: `SELECT ROUND(CAST(AVG(s.weight_kg) AS DECIMAL), 2) AS average_weight_kg FROM superhero AS s JOIN gender AS g ON g.id = s.gender_id JOIN alignment AS a ON a.id = s.alignment_id WHERE g.gender = 'Female' AND a.alignment = 'Good' AND s.weight_kg > 0`
- Detail: {"missing_tables": ["gender"], "missing_cols": []}

## bird-379 (bird, challenging) -> **missing_table**
- Q: What percentage of Marvel Comics superheroes with a recorded superpower are classified as good? Round the percentage to two decimal places, and give me just that single value.
- Evidence: Good means alignment 'Good'; superpower refers to a hero's recorded power.
- Gold: `SELECT ROUND(CAST(CASE WHEN (SUM(CASE WHEN a.alignment = 'Good' THEN 1 ELSE 0 END)) IS NULL THEN NULL ELSE CAST(COALESCE(SUBSTRING(CAST((SUM(CASE WHEN a.alignment = 'Good' THEN 1 ELSE 0 END)) AS TEXT) FROM '^[[:space:]]*[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?'), '0') AS DOUBLE PRECISION) END * 100 / NULLIF(COUNT(*), 0) AS DECIMAL), 2) AS good_percentage FROM superhero AS s JOIN publi`
- Detail: {"missing_tables": ["publisher"], "missing_cols": []}

## bird-382 (bird, challenging) -> **row_filter**
- Q: Among distinct patients with at least one uric-acid result above the sex-specific upper limit, what is the ratio of male to female patients?
- Evidence: For this task, the uric-acid upper limit is 8.0 for males and 6.5 for females.
- Gold: `SELECT CASE WHEN (SUM(CASE WHEN p.sex = 'M' THEN 1 ELSE 0 END)) IS NULL THEN NULL ELSE CAST(COALESCE(SUBSTRING(CAST((SUM(CASE WHEN p.sex = 'M' THEN 1 ELSE 0 END)) AS TEXT) FROM '^[[:space:]]*[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?'), '0') AS DOUBLE PRECISION) END / NULLIF(NULLIF(SUM(CASE WHEN p.sex = 'F' THEN 1 ELSE 0 END), 0), 0) FROM patient AS p WHERE (p.sex = 'M' AND EXISTS(SELEC`
- Detail: {"predicates": {"patient": "lower(\"sex\"::text) = lower('male')"}, "err": ""}

## bird-389 (bird, challenging) -> **missing_table**
- Q: How many distinct female patients have a normal anti-Scl-70 result and no recorded non-null symptom on any examination?
- Evidence: Normal anti-Scl-70 is recorded as 'negative' or '0'.
- Gold: `SELECT COUNT(*) FROM patient AS p WHERE p.sex = 'F' AND EXISTS(SELECT 1 FROM laboratory AS l WHERE l.id = p.id AND l.sc170 IN ('negative', '0')) AND NOT EXISTS(SELECT 1 FROM examination AS e WHERE e.id = p.id AND NOT e.symptoms IS NULL)`
- Detail: {"missing_tables": ["laboratory"], "missing_cols": []}

## bird-392 (bird, challenging) -> **missing_column**
- Q: I'm describing our young-patient group and want to show how unusual a raised RNP antibody is in these patients. Could you tell me how many patients in the thrombosis cohort born after 1 January 1960 never had a raised RNP antibody result? A few points: the group should cover every patient born after that date, including patients with no laboratory results at all - they count as never having had a raised result. "Raised" means a result strictly above 10, so a result of exactly 10 doesn't count, and a result of "negative" (no antibody detected) is never raised. Please return just one row with a single integer: the number of these patients.
- Evidence: RNP: anti-ribonuclear protein antibody; a result of "negative" means no antibody was detected. A raised RNP result is a laboratory result strictly above 10.
- Gold: `SELECT COUNT(*) AS patient_count FROM patient AS p WHERE p.birthday > '1960-01-01' AND NOT EXISTS(SELECT 1 FROM laboratory AS l WHERE l.id = p.id AND NOT l.rnp IS NULL AND l.rnp <> 'negative' AND CASE WHEN (l.rnp) IS NULL THEN NULL ELSE CAST(COALESCE(SUBSTRING(CAST((l.rnp) AS TEXT) FROM '^[[:space:]]*[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?'), '0') AS DOUBLE PRECISION) END > 10)`
- Detail: {"missing_cols": ["patient.birthday"]}

## bird-394 (bird, challenging) -> **missing_column**
- Q: I'm studying antibody and platelet profiles in mixed connective tissue disease (MCTD). Can you tell me how many patients diagnosed with MCTD alone - meaning MCTD is their only recorded diagnosis - have had at least one platelet reading within the normal range and at least one anti-RNP antibody level above 5 (strictly greater than 5)? I just need the patient count.
- Evidence: A platelet level within the normal range means from 100 to 400, both ends included; below 100 or above 400 is outside the normal range.
- Gold: `SELECT COUNT(DISTINCT t1.id) AS patient_count FROM patient AS t1 WHERE t1.diagnosis = 'MCTD' AND t1.id IN (SELECT id FROM laboratory WHERE plt BETWEEN 100 AND 400) AND t1.id IN (SELECT id FROM laboratory WHERE CASE WHEN (rnp) IS NULL THEN NULL ELSE CAST(COALESCE(SUBSTRING(CAST((rnp) AS TEXT) FROM '^[[:space:]]*[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?'), '0') AS DOUBLE PRECISION) END >`
- Detail: {"missing_cols": ["laboratory.plt"]}

## bird-4 (bird, simple) -> **missing_column**
- Q: What are the mailing street address and name of the school with the seventh-highest recorded average mathematics score?
- Evidence: 
- Gold: `SELECT sc.mailstreet, sc.school FROM satscores AS sat JOIN schools AS sc ON sc.cdscode = sat.cds WHERE sat.rtype = 'S' AND NOT sat.avgscrmath IS NULL ORDER BY sat.avgscrmath DESC NULLS LAST, sat.cds NULLS FIRST LIMIT 1 OFFSET 6`
- Detail: {"missing_cols": ["satscores.avgscrmath"]}

## bird-416 (bird, challenging) -> **row_filter**
- Q: I'm reviewing renal function in the thrombosis cohort and want to compare how often creatinine runs out of the normal range between men and women. For each sex (M and F), please give me: the number of patients of that sex with at least one creatinine result out of the normal range, the total number of patients of that sex, and the share those patients represent of that sex's total as a percentage rounded to one decimal place. Rules: out of the normal range means a creatinine result of 1.5 or higher; the total per sex counts every patient of that sex on file whether or not any lab result exists for them.
- Evidence: Creatinine out of the normal range: a CRE value of 1.5 or higher. Male is SEX = 'M'; female is SEX = 'F'.
- Gold: `SELECT p.sex AS sex, COUNT(DISTINCT CASE WHEN l.cre >= 1.5 THEN p.id END) AS out_of_range_patients, COUNT(DISTINCT p.id) AS total_patients, ROUND(CAST(100.0 * COUNT(DISTINCT CASE WHEN l.cre >= 1.5 THEN p.id END) / NULLIF(COUNT(DISTINCT p.id), 0) AS DECIMAL), 1) AS share_pct FROM patient AS p LEFT JOIN laboratory AS l ON p.id = l.id WHERE p.sex IN ('M', 'F') GROUP BY p.sex ORDER BY p.sex NULLS FIRS`
- Detail: {"predicates": {"patient": "(lower(\"sex\"::text) = lower('M')) AND (lower(\"sex\"::text) = lower('F'))"}, "err": ""}

## bird-417 (bird, challenging) -> **row_filter**
- Q: In this cohort, I want to compare the most extreme total cholesterol (T-CHO) readings between patients admitted to the hospital and those followed at the outpatient clinic. Please give me, for each of the two groups, the single highest T-CHO reading, along with the admission status ('+' admitted, '-' outpatient) and the patient ID whose reading is the group's highest. List the admitted group's row first, then the outpatient group's. If several patients tie at a group's highest reading, list each of them.
- Evidence: T-CHO: total cholesterol. '+': the patient was admitted to the hospital. '-': the patient was followed at the outpatient clinic.
- Gold: `SELECT l."T-CHO" AS "T-CHO", p.admission AS status, p.id FROM patient AS p JOIN laboratory AS l ON l.id = p.id JOIN (SELECT p2.admission AS adm, MAX(l2."T-CHO") AS mx FROM patient AS p2 JOIN laboratory AS l2 ON l2.id = p2.id WHERE p2.admission IN ('+', '-') GROUP BY p2.admission) AS t ON t.adm = p.admission AND t.mx = l."T-CHO" ORDER BY CASE p.admission WHEN '+' THEN 0 ELSE 1 END NULLS FIRST, p.id`
- Detail: {"predicates": {"patient": "(lower(\"admission\"::text) = lower('+')) AND (lower(\"admission\"::text) = lower('-'))"}, "err": ""}

## bird-418 (bird, challenging) -> **missing_column**
- Q: Among patients whose first visit to the hospital was in 1991, which patients mounted the strongest anti-ribonuclear protein (RNP) response? Please give me the patient ID and anti-RNP level for every patient tied at the highest recorded level. Only consider patients for whom a level was actually recorded.
- Evidence: anti-ribonuclear protein (RNP): an antibody titer; a higher titer means a higher level.
- Gold: `SELECT DISTINCT t1.id, t2.rnp FROM patient AS t1 INNER JOIN laboratory AS t2 ON t1.id = t2.id WHERE EXTRACT(YEAR FROM CAST(t1."First Date" AS TIMESTAMP)) = '1991' AND NOT t2.rnp IS NULL AND CASE WHEN (t2.rnp) IS NULL THEN NULL ELSE CAST(COALESCE(SUBSTRING(CAST((t2.rnp) AS TEXT) FROM '^[[:space:]]*[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?'), '0') AS DOUBLE PRECISION) END = (SELECT MAX(C`
- Detail: {"missing_cols": ["patient.First Date"]}

## bird-424 (bird, challenging) -> **row_filter**
- Q: For a study of laboratory test patterns, I need to size a cohort. How many female patients have at least one anti-DNA antibody level below 8 (the upper bound of the normal range)? Any laboratory visit of the patient qualifies; there is no time scope. I just need that single count back.
- Evidence: anti-DNA level: the anti-DNA antibody concentration measured in the laboratory tests
- Gold: `SELECT COUNT(DISTINCT t1.id) AS patient_count FROM patient AS t1 INNER JOIN laboratory AS t2 ON t1.id = t2.id WHERE t1.sex = 'F' AND CASE WHEN (t2.dna) IS NULL THEN NULL ELSE CAST(COALESCE(SUBSTRING(CAST((t2.dna) AS TEXT) FROM '^[[:space:]]*[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?'), '0') AS DOUBLE PRECISION) END < 8`
- Detail: {"predicates": {"patient": "lower(\"sex\"::text) = lower('female')"}, "err": ""}

## bird-430 (bird, challenging) -> **row_filter**
- Q: In the thrombosis and autoimmune-disease cohort, I want to compare how often lactate dehydrogenase stays in the normal range between patients admitted to the hospital and patients followed at the outpatient clinic. Please give me one row per patient group showing the number of lactate dehydrogenase measurements within the normal range recorded for that group, with the admitted group's row first. Label the rows 'admitted to the hospital' for the Admission = '+' group and 'followed at the outpatient clinic' for the Admission = '-' group. Every laboratory measurement recorded for those patients across the whole study period counts. Nothing else is needed.
- Evidence: The normal range for lactate dehydrogenase means a value below 500.
- Gold: `SELECT CASE WHEN p.admission = '+' THEN 'admitted to the hospital' ELSE 'followed at the outpatient clinic' END AS patient_group, COUNT(*) AS normal_ldh_measurements FROM patient AS p JOIN laboratory AS l ON p.id = l.id WHERE p.admission IN ('+', '-') AND l.ldh < 500 GROUP BY 1 ORDER BY patient_group`
- Detail: {"predicates": {"patient": "(lower(\"admission\"::text) = lower('+')) AND (lower(\"admission\"::text) = lower('-'))"}, "err": ""}

## bird-438 (bird, challenging) -> **view_semantics**
- Q: I'm reviewing patients with an elevated anti-ribonuclear protein result. Among patients who ever had an anti-ribonuclear protein result of 16 or higher, I want to follow up the three whose liver enzymes stayed in the normal range. The normal range for GPT is below 60. For each patient, take their highest GPT value among their laboratory tests that fall in the normal range. Rank patients from that highest value down; if two patients share the same value, the one with the smaller patient ID comes first. Please return exactly three patients, one row per patient, with only each patient's Birthday.
- Evidence: GPT stands for glutamic pyruvic transaminase, a liver enzyme; anti-ribonuclear protein is an autoantibody measured in laboratory tests.
- Gold: `SELECT t1.birthday FROM patient AS t1 INNER JOIN laboratory AS t2 ON t1.id = t2.id WHERE t2.gpt < 60 AND t1.id IN (SELECT id FROM laboratory WHERE CASE WHEN (rnp) IS NULL THEN NULL ELSE CAST(COALESCE(SUBSTRING(CAST((rnp) AS TEXT) FROM '^[[:space:]]*[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?'), '0') AS DOUBLE PRECISION) END >= 16) GROUP BY t1.id ORDER BY MAX(t2.gpt) DESC NULLS LAST, t1.i`
- Detail: {"err": "GroupingError: column \"t1.birthday\" must appear in the GROUP BY clause or be used in an aggregate function"}

## bird-442 (bird, challenging) -> **missing_column**
- Q: I'm reviewing how often older female patients show elevated anti-RNP antibody results, split by whether they were admitted to the hospital or followed at the outpatient clinic. For female patients aged at least 50 as of 2026-10-09, please give me a two-row breakdown by care setting (admitted to the hospital vs. followed at the outpatient clinic), showing for each setting how many patients had at least one anti-RNP laboratory result of at least 4, and how many had no such result. A patient's admission marker of '+' counts as admitted to the hospital and '-' counts as followed at the outpatient clinic; patients with any other admission marker are out of scope. Order the two rows alphabetically by care setting.
- Evidence: anti-RNP: anti-ribonuclear protein antibody, measured in laboratory results; admission marker: the patient's recorded admission sign.
- Gold: `SELECT CASE WHEN p.admission = '+' THEN 'admitted to the hospital' ELSE 'followed at the outpatient clinic' END AS care_setting, SUM(CASE WHEN EXISTS(SELECT 1 FROM laboratory AS l WHERE l.id = p.id AND CASE WHEN (l.rnp) IS NULL THEN NULL ELSE CAST(COALESCE(SUBSTRING(CAST((l.rnp) AS TEXT) FROM '^[[:space:]]*[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?'), '0') AS DOUBLE PRECISION) END >= 4)`
- Detail: {"missing_cols": ["patient.birthday"]}

## bird-444 (bird, challenging) -> **missing_column**
- Q: Among all patients diagnosed with systemic lupus erythematosus, I want to find the patient whose anti-DNA test result was the strongest ever recorded for that disease. Please report the patient's identifier, the patient's diagnosis, and that patient's highest anti-DNA test result, using the number exactly as the test wrote it. If several patients tie for the highest anti-DNA result, list every tied patient.
- Evidence: Systemic lupus erythematosus (SLE) is an autoimmune disease; anti-DNA is an antibody test reported as a number.
- Gold: `WITH ranked AS (SELECT p.id AS patient_id, p.diagnosis AS diagnosis, l.dna AS highest_anti_dna, ROW_NUMBER() OVER (PARTITION BY p.id ORDER BY CASE WHEN (l.dna) IS NULL THEN NULL ELSE CAST(COALESCE(SUBSTRING(CAST((l.dna) AS TEXT) FROM '^[[:space:]]*[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?'), '0') AS DOUBLE PRECISION) END DESC NULLS LAST, l.date DESC NULLS LAST) AS rn FROM patient AS p `
- Detail: {"missing_cols": ["laboratory.date"]}

## bird-447 (bird, challenging) -> **row_filter**
- Q: In the thrombosis prediction cohort, I want to gauge how often the most recent anti-ribonuclear protein measurement among female patients was markedly elevated while CPK stayed low at that same measurement. Please give me a single integer: the number of female patients whose most recent anti-ribonuclear protein titer was above 64 and whose CPK from that same laboratory record was below 250. Above 64 means strictly greater than 64, and below 250 means strictly less than 250.
- Evidence: Anti-ribonuclear protein is an autoantibody measured as a titer in the blood; a negative result means the antibody was not detected.
- Gold: `SELECT COUNT(DISTINCT p.id) AS female_patients FROM patient AS p JOIN laboratory AS l ON l.id = p.id WHERE p.sex = 'F' AND NOT l.rnp IS NULL AND l.date = (SELECT MAX(l2.date) FROM laboratory AS l2 WHERE l2.id = p.id AND NOT l2.rnp IS NULL) AND CASE WHEN (l.rnp) IS NULL THEN NULL ELSE CAST(COALESCE(SUBSTRING(CAST((l.rnp) AS TEXT) FROM '^[[:space:]]*[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]`
- Detail: {"predicates": {"patient": "lower(\"sex\"::text) = lower('female')"}, "err": ""}

## bird-452 (bird, challenging) -> **missing_column**
- Q: I'm reviewing confirmed SLE cases for a study of neurologic involvement. Among patients whose examination lists SLE among the diagnosed diseases and who have a symptom recorded at such an examination, I need the case detail of the youngest such patient. Please send me the symptom recorded at that qualifying examination and that patient's overall diagnosis (their overall diagnosis, not the diagnosis written at the examination). If two patients share the same birth date, use the one with the smaller patient ID; and if that patient has more than one qualifying examination, use the most recent one.
- Evidence: SLE is systemic lupus erythematosus. A disease name followed by 'susp' means the disease was only suspected, not diagnosed.
- Gold: `WITH target AS (SELECT 'SLE' AS d) SELECT e.symptoms, p.diagnosis AS overall_diagnosis FROM patient AS p JOIN examination AS e ON e.id = p.id WHERE NOT p.birthday IS NULL AND NOT e.symptoms IS NULL AND TRIM(CAST(e.symptoms AS TEXT)) <> '' AND EXISTS(SELECT 1 FROM target WHERE REPLACE(',' || REPLACE(e.diagnosis, ' ', '') || ',', ',' || d || ',', '') <> ',' || REPLACE(e.diagnosis, ' ', '') || ',') O`
- Detail: {"missing_cols": ["patient.birthday"]}

## bird-465 (bird, challenging) -> **row_filter**
- Q: I'd like a single number: how many female patients in the thrombosis prediction data have a laboratory record showing a normal white blood cell count, an abnormal fibrinogen level, and an anti-ribonuclear protein (RNP) reading above 15, considering all recorded laboratory dates?
- Evidence: A normal white blood cell count means strictly between 3.5 and 9.0; an abnormal fibrinogen level means at most 150 or at least 450.
- Gold: `SELECT COUNT(DISTINCT p.id) FROM patient AS p JOIN laboratory AS l ON l.id = p.id WHERE p.sex = 'F' AND l.wbc > 3.5 AND l.wbc < 9.0 AND (l.fg <= 150 OR l.fg >= 450) AND CASE WHEN (l.rnp) IS NULL THEN NULL ELSE CAST(COALESCE(SUBSTRING(CAST((l.rnp) AS TEXT) FROM '^[[:space:]]*[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?'), '0') AS DOUBLE PRECISION) END > 15`
- Detail: {"predicates": {"patient": "lower(\"sex\"::text) = lower('female')"}, "err": ""}

## bird-467 (bird, challenging) -> **missing_column**
- Q: I'm preparing a case series on early renal involvement and need to size my cohort. How many patients were under age 50 on the day of a laboratory test performed between 1 January 1981 and 31 December 1986 inclusive, had a platelet count from 100 through 400 at that test, and showed proteinuria at that test? Age means completed years on the day of the test, so under 50 is strictly below 50. The platelet range is inclusive. I just need the number of patients satisfying all conditions.
- Evidence: A patient showed proteinuria at a test when that test's dipstick reading reports protein: a dash or zero means no protein was found, a number is the amount of protein found, TR stands for trace protein, and a reading written in percent signs is the dipstick saturated, the strongest reading.
- Gold: `SELECT COUNT(DISTINCT p.id) AS patient_count FROM patient AS p JOIN laboratory AS l ON l.id = p.id WHERE SUBSTRING(CAST(l.date AS TEXT) FROM 1 FOR 4) BETWEEN '1981' AND '1986' AND l.plt BETWEEN 100 AND 400 AND NOT p.birthday IS NULL AND (CASE WHEN (SUBSTRING(CAST(l.date AS TEXT) FROM 1 FOR 4)) IS NULL THEN NULL ELSE CAST(COALESCE(SUBSTRING(CAST((SUBSTRING(CAST(l.date AS TEXT) FROM 1 FOR 4)) AS TEX`
- Detail: {"missing_cols": ["laboratory.U-PRO", "laboratory.plt", "patient.birthday"]}

## bird-474 (bird, moderate) -> **row_filter**
- Q: What are the bonds that have phosphorus and nitrogen as their atom elements?
- Evidence: 
- Gold: `SELECT t2.bond_id FROM atom AS t1 INNER JOIN connected AS t2 ON t1.atom_id = t2.atom_id WHERE t2.bond_id IN (SELECT t3.bond_id FROM connected AS t3 INNER JOIN atom AS t4 ON t3.atom_id = t4.atom_id WHERE t4.element = 'p') AND t1.element = 'n'`
- Detail: {"predicates": {"atom": "(lower(\"element\"::text) = lower('Phosphorus')) AND (lower(\"element\"::text) = lower('Nitrogen'))"}, "err": ""}

## bird-476 (bird, moderate) -> **row_filter**
- Q: How many atoms occur in molecules that have at least one triple bond and at least one phosphorus or bromine atom?
- Evidence: The '#' bond-type symbol denotes a triple bond.
- Gold: `WITH triple AS (SELECT DISTINCT molecule_id FROM bond WHERE bond_type = '#'), hetero AS (SELECT DISTINCT molecule_id FROM atom WHERE element IN ('p', 'br')), qualified AS (SELECT t.molecule_id FROM triple AS t JOIN hetero AS h ON h.molecule_id = t.molecule_id) SELECT COUNT(*) FROM atom AS a JOIN qualified AS q ON q.molecule_id = a.molecule_id`
- Detail: {"predicates": {"atom": "lower(\"element\"::text) IN (lower('P'), lower('Br'))", "bond": "lower(\"bond_type\"::text) = lower('#')"}, "err": ""}

## bird-489 (bird, challenging) -> **row_filter**
- Q: For a report on structural features of carcinogenic compounds, I'm looking at compounds that form a triple bond. Among those, what percent are labeled carcinogenic and what percent are labeled non-carcinogenic, each rounded to two decimal places? The two percents should sum to 100, apart from rounding.
- Evidence: Label '+' means carcinogenic; label '-' means non-carcinogenic.
- Gold: `SELECT ROUND(CAST(CASE WHEN (COUNT(DISTINCT CASE WHEN m.label = '+' THEN b.molecule_id END)) IS NULL THEN NULL ELSE CAST(COALESCE(SUBSTRING(CAST((COUNT(DISTINCT CASE WHEN m.label = '+' THEN b.molecule_id END)) AS TEXT) FROM '^[[:space:]]*[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?'), '0') AS DOUBLE PRECISION) END * 100 / NULLIF(COUNT(DISTINCT b.molecule_id), 0) AS DECIMAL), 2) AS pct_car`
- Detail: {"predicates": {"bond": "lower(\"bond_type\"::text) = lower('triple')"}, "err": ""}

## bird-492 (bird, challenging) -> **row_filter**
- Q: I'm studying the hydrogen bonding pattern of the molecule that contains the yttrium atom. How many bonds in that molecule have a hydrogen atom at one end? Just give me the single overall count, please.
- Evidence: An yttrium atom has element symbol Y; a hydrogen atom has element symbol H.
- Gold: `SELECT COUNT(DISTINCT c.bond_id) AS bond_count FROM connected AS c JOIN atom AS a ON a.atom_id = c.atom_id OR a.atom_id = c.atom_id2 WHERE a.element = 'h' AND a.molecule_id = (SELECT molecule_id FROM atom WHERE element = 'y')`
- Detail: {"predicates": {"atom": "(lower(\"element\"::text) = lower('Y')) AND (lower(\"element\"::text) = lower('H'))"}, "err": ""}

## bird-6 (bird, moderate) -> **missing_column**
- Q: Which schools served a grade span of Kindergarten to 9th grade in the county of Los Angeles and what is its Percent (%) Eligible FRPM (Ages 5-17)?
- Evidence: FRPM eligibility percentage is free-or-reduced-price meal recipients divided by same-age-band enrollment, times 100.
- Gold: `SELECT t2.school, t1."FRPM Count (Ages 5-17)" * 100 / NULLIF(t1."Enrollment (Ages 5-17)", 0) FROM frpm AS t1 INNER JOIN schools AS t2 ON t1.cdscode = t2.cdscode WHERE t2.county = 'Los Angeles' AND t2.gsserved = 'K-9'`
- Detail: {"missing_cols": ["schools.gsserved"]}

## bird-60 (bird, challenging) -> **missing_table**
- Q: What percentage of Coldsnap card printings have both a Card Kingdom regular-product ID and foil-product ID recorded?
- Evidence: 
- Gold: `SELECT CASE WHEN (SUM(CASE WHEN NOT t1.cardkingdomfoilid IS NULL AND NOT t1.cardkingdomid IS NULL THEN 1 ELSE 0 END)) IS NULL THEN NULL ELSE CAST(COALESCE(SUBSTRING(CAST((SUM(CASE WHEN NOT t1.cardkingdomfoilid IS NULL AND NOT t1.cardkingdomid IS NULL THEN 1 ELSE 0 END)) AS TEXT) FROM '^[[:space:]]*[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?'), '0') AS DOUBLE PRECISION) END * 100 / NULLIF`
- Detail: {"missing_tables": ["sets"], "missing_cols": ["cards.setcode"]}

## bird-66 (bird, challenging) -> **missing_column**
- Q: I'm preparing a multilingual catalog and want to gauge how much localizable content exists per kind of set. For every set type, I need the number of sets of that type that have an officially translated name, and the total number of cards in those sets. Please include every set type in the results, even ones where no set has an officially translated name (show zero for both values in that case), and sort the results alphabetically by set type.
- Evidence: Set type: the expansion type of a set, such as core, expansion or promo. Officially translated name: the set's name rendered in another language, such as Italian or Chinese Traditional.
- Gold: `SELECT s.type, SUM(CASE WHEN EXISTS(SELECT 1 FROM set_translations AS t WHERE t.setcode = s.code) THEN 1 ELSE 0 END) AS sets_with_translation, SUM(CASE WHEN EXISTS(SELECT 1 FROM set_translations AS t WHERE t.setcode = s.code) THEN s.totalsetsize ELSE 0 END) AS total_cards FROM sets AS s GROUP BY s.type ORDER BY s.type NULLS FIRST`
- Detail: {"missing_cols": ["sets.totalsetsize"]}

## bird-77 (bird, challenging) -> **row_filter**
- Q: I'm putting together a showcase of instant-speed cards from Magic: The Gathering. Which cards in the Dark Ascension set have the Flash keyword and, among those, the highest converted mana cost? Please list just the card names, one row per card, alphabetically by name, and include every card that ties on that highest cost.
- Evidence: Dark Ascension is the Magic: The Gathering set named 'Dark Ascension'. Flash is the keyword that lets a card be cast any time you could cast an instant. Converted mana cost is the total amount of mana a card costs to cast.
- Gold: `SELECT t1.name FROM cards AS t1 INNER JOIN sets AS t2 ON t2.code = t1.setcode WHERE t2.name = 'Dark Ascension' AND POSITION(',' || 'Flash' || ',' IN ',' || t1.keywords || ',') > 0 AND t1.convertedmanacost = (SELECT MAX(t3.convertedmanacost) FROM cards AS t3 INNER JOIN sets AS t4 ON t4.code = t3.setcode WHERE t4.name = 'Dark Ascension' AND POSITION(',' || 'Flash' || ',' IN ',' || t3.keywords || ','`
- Detail: {"predicates": {"cards": "lower(\"setcode\"::text) = lower('DARK')"}, "err": ""}

## bird-78 (bird, challenging) -> **missing_column**
- Q: I'm preparing localized set icon assets and need to know the foreign-language name coverage of every Magic: The Gathering set released in 2020. For each set released in 2020 (meaning its release date falls within the calendar year 2020), please give me the set's name, its keyrune code, and the number of languages in which the set has an official translated name. Nothing else.
- Evidence: keyrune code: the code for the set's image icon; official translated name: the set's name rendered in a foreign language by the game's publisher.
- Gold: `SELECT s.name, s.keyrunecode, COUNT(DISTINCT st.language) AS translated_languages FROM sets AS s LEFT JOIN set_translations AS st ON st.setcode = s.code AND NOT st.translation IS NULL WHERE EXTRACT(YEAR FROM CAST(s.releasedate AS TIMESTAMP)) = '2020' GROUP BY s.id, s.name, s.keyrunecode ORDER BY s.name NULLS FIRST`
- Detail: {"missing_cols": ["set_translations.translation", "sets.releasedate"]}

## bird-79 (bird, challenging) -> **missing_column**
- Q: I'm sizing a catalogue page of 2017 sets that were localized for international markets. How many cards were there in total across the Magic: The Gathering sets released in 2017 (between January 1 and December 31, 2017) that have a name in a language other than English? A set counts as localized if its name has a foreign-language translation. Include every card in each qualifying set, counting promotional and related supplemental printings as part of the set. I just need the single total across all qualifying sets, not per-set numbers.
- Evidence: A foreign-language translation is a set's name rendered in a language other than English (e.g. Chinese Simplified, German, Spanish).
- Gold: `SELECT SUM(s.totalsetsize) AS total_cards FROM sets AS s WHERE s.releasedate BETWEEN '2017-01-01' AND '2017-12-31' AND EXISTS(SELECT 1 FROM set_translations AS t WHERE t.setcode = s.code)`
- Detail: {"missing_cols": ["sets.releasedate", "sets.totalsetsize"]}

## bird-8 (bird, challenging) -> **missing_column**
- Q: List the distinct available administrator email addresses for public intermediate/middle schools in San Bernardino city and county, in a unified school district, opened during 2009 or 2010.
- Evidence: 
- Gold: `WITH matched AS (SELECT admemail1, admemail2, admemail3 FROM schools WHERE county = 'San Bernardino' AND city = 'San Bernardino' AND doctype = 'Unified School District' AND soctype = 'Intermediate/Middle Schools (Public)' AND opendate >= '2009-01-01' AND opendate < '2011-01-01') SELECT admemail1 AS email FROM matched WHERE NOT admemail1 IS NULL AND TRIM(CAST(admemail1 AS TEXT)) <> '' UNION SELECT `
- Detail: {"missing_cols": ["schools.doctype"]}

## bird-91 (bird, challenging) -> **row_filter**
- Q: I play paper Magic and I'm building a pauper deck. How many printings of cards illustrated by Erica Yang are legal in the pauper format and exist as paper (physically printed) cards? I want just a single count of printings, with each printing counted separately.
- Evidence: Pauper is a Magic: The Gathering format where only common-rarity cards are legal; a printing is a specific physical or digital release of a card in a set; 'legal in pauper' means the card's pauper legality status is Legal; 'paper' means a physical printed card.
- Gold: `SELECT COUNT(*) AS paper_pauper_printings FROM cards AS c INNER JOIN legalities AS l ON c.uuid = l.uuid WHERE c.artist = 'Erica Yang' AND l.format = 'pauper' AND l.status = 'Legal' AND CAST(c.availability AS TEXT) LIKE '%paper%'`
- Detail: {"predicates": {"cards": "(lower(\"artist\"::text) = lower('Erica Yang')) AND (lower(\"rarity\"::text) = lower('Common'))", "legalities": "(lower(\"format\"::text) = lower('Pauper')) AND (lower(\"status\"::text) = lower('Legal'))"}, "err": ""}

## spider-115 (spider, hard) -> **missing_column**
- Q: How many car models are produced in the usa?
- Evidence: 
- Gold: `SELECT COUNT(*) FROM "model_list" AS "t1" JOIN "car_makers" AS "t2" ON "t1"."maker" = "t2"."id" JOIN "countries" AS "t3" ON "t2"."country" = "t3"."countryid" WHERE "t3"."countryname" = 'usa'`
- Detail: {"missing_cols": ["countries.countryname"]}

## spider-149 (spider, medium) -> **view_semantics**
- Q: Which makers designed more than 3 car models? List full name and the id.
- Evidence: 
- Gold: `SELECT "t1"."fullname", "t1"."id" FROM "car_makers" AS "t1" JOIN "model_list" AS "t2" ON "t1"."id" = "t2"."maker" GROUP BY "t1"."id" HAVING COUNT(*) > 3`
- Detail: {"err": "GroupingError: column \"t1.fullname\" must appear in the GROUP BY clause or be used in an aggregate function"}

## spider-151 (spider, extra) -> **row_filter**
- Q: Which distinctive models are produced by maker with the full name General Motors or weighing more than 3500?
- Evidence: 
- Gold: `SELECT DISTINCT "t2"."model" FROM "car_names" AS "t1" JOIN "model_list" AS "t2" ON "t1"."model" = "t2"."model" JOIN "car_makers" AS "t3" ON "t2"."maker" = "t3"."id" JOIN "cars_data" AS "t4" ON "t1"."makeid" = "t4"."id" WHERE "t3"."fullname" = 'General Motors' OR "t4"."weight" > 3500`
- Detail: {"predicates": {"car_makers": "lower(\"fullname\"::text) = lower('General Motors')"}, "err": ""}

## spider-175 (spider, extra) -> **view_semantics**
- Q: Which are the car makers which produce at least 2 models and more than 3 car makers ? List the id and the maker .
- Evidence: 
- Gold: `SELECT "t1"."id", "t1"."maker" FROM "car_makers" AS "t1" JOIN "model_list" AS "t2" ON "t1"."id" = "t2"."maker" GROUP BY "t1"."id" HAVING COUNT(*) >= 2 INTERSECT SELECT "t1"."id", "t1"."maker" FROM "car_makers" AS "t1" JOIN "model_list" AS "t2" ON "t1"."id" = "t2"."maker" JOIN "car_names" AS "t3" ON "t2"."model" = "t3"."model" GROUP BY "t1"."id" HAVING COUNT(*) > 3`
- Detail: {"err": "GroupingError: column \"t1.maker\" must appear in the GROUP BY clause or be used in an aggregate function"}

## spider-25 (spider, extra) -> **view_semantics**
- Q: What is the name and capacity of the stadium with the most concerts after 2013 ?
- Evidence: 
- Gold: `SELECT "t2"."name", "t2"."capacity" FROM "concert" AS "t1" JOIN "stadium" AS "t2" ON "t1"."stadium_id" = "t2"."stadium_id" WHERE "t1"."year" > 2013 GROUP BY "t2"."stadium_id" ORDER BY COUNT(*) DESC NULLS LAST LIMIT 1`
- Detail: {"err": "GroupingError: column \"t2.name\" must appear in the GROUP BY clause or be used in an aggregate function"}

## spider-356 (spider, medium) -> **missing_column**
- Q: Return the ids corresponding to templates with the description 'Presentation'.
- Evidence: 
- Gold: `SELECT "t2"."template_id" FROM "ref_template_types" AS "t1" JOIN "templates" AS "t2" ON "t1"."template_type_code" = "t2"."template_type_code" WHERE "t1"."template_type_description" = 'Presentation'`
- Detail: {"missing_cols": ["ref_template_types.template_type_description"]}

## spider-504 (spider, extra) -> **row_filter**
- Q: List the name and date the battle that has lost the ship named 'Lettice' and the ship named 'HMS Atalanta'
- Evidence: 
- Gold: `SELECT "t1"."name", "t1"."date" FROM "battle" AS "t1" JOIN "ship" AS "t2" ON "t1"."id" = "t2"."lost_in_battle" WHERE "t2"."name" = 'Lettice' INTERSECT SELECT "t1"."name", "t1"."date" FROM "battle" AS "t1" JOIN "ship" AS "t2" ON "t1"."id" = "t2"."lost_in_battle" WHERE "t2"."name" = 'HMS Atalanta'`
- Detail: {"predicates": {"ship": "(lower(\"name\"::text) = lower('Lettice')) AND (lower(\"name\"::text) = lower('HMS Atalanta'))"}, "err": ""}

## spider-512 (spider, easy) -> **missing_column**
- Q: What are the descriptions for all the math courses?
- Evidence: 
- Gold: `SELECT "course_description" FROM "courses" WHERE "course_name" = 'math'`
- Detail: {"missing_cols": ["courses.course_name"]}

## spider-540 (spider, extra) -> **view_semantics**
- Q: What is the program id and the summary of the degree that has the most students enrolled?
- Evidence: 
- Gold: `SELECT "t1"."degree_program_id", "t1"."degree_summary_name" FROM "degree_programs" AS "t1" JOIN "student_enrolment" AS "t2" ON "t1"."degree_program_id" = "t2"."degree_program_id" GROUP BY "t1"."degree_program_id" ORDER BY COUNT(*) DESC NULLS LAST LIMIT 1`
- Detail: {"err": "GroupingError: column \"t1.degree_summary_name\" must appear in the GROUP BY clause or be used in an aggregate function"}

## spider-58 (spider, extra) -> **row_filter**
- Q: What are the first names of every student who has a cat or dog as a pet?
- Evidence: 
- Gold: `SELECT DISTINCT "t1"."fname" FROM "student" AS "t1" JOIN "has_pet" AS "t2" ON "t1"."stuid" = "t2"."stuid" JOIN "pets" AS "t3" ON "t3"."petid" = "t2"."petid" WHERE "t3"."pettype" = 'cat' OR "t3"."pettype" = 'dog'`
- Detail: {"predicates": {"pets": "(lower(\"pettype\"::text) = lower('cat')) AND (lower(\"pettype\"::text) = lower('dog'))"}, "err": ""}

## spider-593 (spider, medium) -> **row_filter**
- Q: List the title of all cartoon directed by "Ben Jones" or "Brandon Vietti".
- Evidence: 
- Gold: `SELECT "title" FROM "cartoon" WHERE "directed_by" = 'Ben Jones' OR "directed_by" = 'Brandon Vietti'`
- Detail: {"predicates": {"cartoon": "(lower(\"directed_by\"::text) = lower('Ben Jones')) AND (lower(\"directed_by\"::text) = lower('Brandon Vietti'))"}, "err": ""}

## spider-610 (spider, medium) -> **row_filter**
- Q: What is the series name of the TV Channel that shows the cartoon "The Rise of the Blue Beetle"?
- Evidence: 
- Gold: `SELECT "t1"."series_name" FROM "tv_channel" AS "t1" JOIN "cartoon" AS "t2" ON "t1"."id" = "t2"."channel" WHERE "t2"."title" = 'The Rise of the Blue Beetle!'`
- Detail: {"predicates": {"cartoon": "lower(\"title\"::text) = lower('The Rise of the Blue Beetle')"}, "err": ""}

## spider-637 (spider, extra) -> **row_filter**
- Q: Find the series name and country of the tv channel that is playing some cartoons directed by Ben Jones and Michael Chang?
- Evidence: 
- Gold: `SELECT "t1"."series_name", "t1"."country" FROM "tv_channel" AS "t1" JOIN "cartoon" AS "t2" ON "t1"."id" = "t2"."channel" WHERE "t2"."directed_by" = 'Michael Chang' INTERSECT SELECT "t1"."series_name", "t1"."country" FROM "tv_channel" AS "t1" JOIN "cartoon" AS "t2" ON "t1"."id" = "t2"."channel" WHERE "t2"."directed_by" = 'Ben Jones'`
- Detail: {"predicates": {"cartoon": "(lower(\"directed_by\"::text) = lower('Ben Jones')) AND (lower(\"directed_by\"::text) = lower('Michael Chang'))"}, "err": ""}

## spider-66 (spider, extra) -> **missing_column**
- Q: What is the first name of every student who has a dog but does not have a cat?
- Evidence: 
- Gold: `SELECT "t1"."fname", "t1"."age" FROM "student" AS "t1" JOIN "has_pet" AS "t2" ON "t1"."stuid" = "t2"."stuid" JOIN "pets" AS "t3" ON "t3"."petid" = "t2"."petid" WHERE "t3"."pettype" = 'dog' AND NOT "t1"."stuid" IN (SELECT "t1"."stuid" FROM "student" AS "t1" JOIN "has_pet" AS "t2" ON "t1"."stuid" = "t2"."stuid" JOIN "pets" AS "t3" ON "t3"."petid" = "t2"."petid" WHERE "t3"."pettype" = 'cat')`
- Detail: {"missing_cols": ["student.age"]}

## spider-684 (spider, hard) -> **missing_table**
- Q: What are the names of people who do not play poker?
- Evidence: 
- Gold: `SELECT "name" FROM "people" WHERE NOT "people_id" IN (SELECT "people_id" FROM "poker_player")`
- Detail: {"missing_tables": ["poker_player"], "missing_cols": []}

## spider-714 (spider, medium) -> **missing_column**
- Q: What are the population and life expectancies in Brazil?
- Evidence: 
- Gold: `SELECT "population", "lifeexpectancy" FROM "country" WHERE "name" = 'Brazil'`
- Detail: {"missing_cols": ["country.name"]}

## spider-783 (spider, hard) -> **row_filter**
- Q: Return the codes of countries that do not speak English and do not have Republics for governments.
- Evidence: 
- Gold: `SELECT "code" FROM "country" WHERE "governmentform" <> 'Republic' EXCEPT SELECT "countrycode" FROM "countrylanguage" WHERE "language" = 'English'`
- Detail: {"predicates": {"country": "lower(\"governmentform\"::text) = lower('Republic')", "countrylanguage": "lower(\"language\"::text) = lower('English')"}, "err": ""}

## spider-82 (spider, medium) -> **view_semantics**
- Q: What is the first name and gender of the all the students who have more than one pet?
- Evidence: 
- Gold: `SELECT "t1"."fname", "t1"."sex" FROM "student" AS "t1" JOIN "has_pet" AS "t2" ON "t1"."stuid" = "t2"."stuid" GROUP BY "t1"."stuid" HAVING COUNT(*) > 1`
- Detail: {"err": "GroupingError: column \"t1.fname\" must appear in the GROUP BY clause or be used in an aggregate function"}

## spider-890 (spider, hard) -> **row_filter**
- Q: Show the names of all of the high schooler Kyle's friends.
- Evidence: 
- Gold: `SELECT "t3"."name" FROM "friend" AS "t1" JOIN "highschooler" AS "t2" ON "t1"."student_id" = "t2"."id" JOIN "highschooler" AS "t3" ON "t1"."friend_id" = "t3"."id" WHERE "t2"."name" = 'Kyle'`
- Detail: {"predicates": {"highschooler": "lower(\"name\"::text) = lower('Kyle')"}, "err": ""}

## spider-922 (spider, extra) -> **view_semantics**
- Q: Which professionals live in the state of Indiana or have done treatment on more than 2 treatments? List his or her id, last name and cell phone.
- Evidence: 
- Gold: `SELECT "professional_id", "last_name", "cell_number" FROM "professionals" WHERE "state" = 'Indiana' UNION SELECT "t1"."professional_id", "t1"."last_name", "t1"."cell_number" FROM "professionals" AS "t1" JOIN "treatments" AS "t2" ON "t1"."professional_id" = "t2"."professional_id" GROUP BY "t1"."professional_id" HAVING COUNT(*) > 2`
- Detail: {"err": "GroupingError: column \"t1.last_name\" must appear in the GROUP BY clause or be used in an aggregate function"}

## spider-937 (spider, extra) -> **view_semantics**
- Q: Tell me the owner id and last name of the owner who spent the most on treatments of his or her dogs.
- Evidence: 
- Gold: `SELECT "t1"."owner_id", "t1"."last_name" FROM "owners" AS "t1" JOIN "dogs" AS "t2" ON "t1"."owner_id" = "t2"."owner_id" JOIN "treatments" AS "t3" ON "t2"."dog_id" = "t3"."dog_id" GROUP BY "t1"."owner_id" ORDER BY COUNT(*) DESC NULLS LAST LIMIT 1`
- Detail: {"err": "GroupingError: column \"t1.last_name\" must appear in the GROUP BY clause or be used in an aggregate function"}

## spider-938 (spider, extra) -> **view_semantics**
- Q: What is the description of the treatment type that costs the least money in total?
- Evidence: 
- Gold: `SELECT "t1"."treatment_type_description" FROM "treatment_types" AS "t1" JOIN "treatments" AS "t2" ON "t1"."treatment_type_code" = "t2"."treatment_type_code" GROUP BY "t1"."treatment_type_code" ORDER BY SUM("cost_of_treatment") ASC NULLS FIRST LIMIT 1`
- Detail: {"err": "GroupingError: column \"t1.treatment_type_description\" must appear in the GROUP BY clause or be used in an aggregate function"}
