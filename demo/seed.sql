-- Demo data: a plausible mid-week list for a two-person household.
--
-- Nothing here is real. It exists so that a fresh clone shows the app doing
-- its actual job (store memory, in-store mode, usuals, bought-today) instead
-- of an empty board, and so the screenshots in the README can be regenerated
-- by anyone.
--
--   make demo          brings the stack up and loads this file
--   make demo-reset    wipes these rows and loads them again
--
-- Safe to run only on a throwaway database: it inserts, it does not merge.
-- The stores themselves are created by the app at startup, so this file looks
-- them up by name and never assumes an id.

begin;

-- Items: the household's memory of where each thing is normally bought.
insert into items (name, name_norm, category, home_store) values
  ('Paper towels',      'paper towels',      'household', (select id from stores where name = 'Costco')),
  ('Rotisserie chicken','rotisserie chicken','deli',      (select id from stores where name = 'Costco')),
  ('Olive oil',         'olive oil',         'pantry',    (select id from stores where name = 'Costco')),
  ('Bananas',           'bananas',           'produce',   (select id from stores where name = 'Aldi')),
  ('Greek yogurt',      'greek yogurt',      'dairy',     (select id from stores where name = 'Aldi')),
  ('Sourdough',         'sourdough',         'bakery',    (select id from stores where name = 'Aldi')),
  ('Dish soap',         'dish soap',         'household', (select id from stores where name = 'Walmart')),
  ('AA batteries',      'aa batteries',      'household', (select id from stores where name = 'Walmart')),
  ('Strawberries',      'strawberries',      'produce',   (select id from stores where name = 'Farmers Market')),
  ('Basil',             'basil',             'produce',   (select id from stores where name = 'Farmers Market')),
  ('Rice noodles',      'rice noodles',      'pantry',    (select id from stores where name = 'Asian Market')),
  ('Sunscreen',         'sunscreen',         '',          null),
  ('Milk',              'milk',              'dairy',     (select id from stores where name = 'Aldi')),
  ('Eggs',              'eggs',              'dairy',     (select id from stores where name = 'Aldi')),
  ('Coffee beans',      'coffee beans',      'pantry',    (select id from stores where name = 'Costco'))
on conflict (name_norm) do nothing;

-- The category-level fallback, learned rather than guessed: an unknown item
-- in a known category starts at that category's usual store.
insert into category_defaults (category, store_id) values
  ('produce',   (select id from stores where name = 'Farmers Market')),
  ('household', (select id from stores where name = 'Walmart')),
  ('dairy',     (select id from stores where name = 'Aldi'))
on conflict (category) do nothing;

-- Currently on the list.
insert into entries (item_id, qty, note, planned_store, added_by, added_at)
select i.id, v.qty, v.note,
       (select id from stores where name = v.store),
       v.who, now() - (v.age || ' hours')::interval
from (values
  ('paper towels',       '1 pack', '',                 'Costco',         'Willian', 30),
  ('rotisserie chicken', '1',      'for Thursday',     'Costco',         'Aline',   29),
  ('olive oil',          '',       'the big tin',      'Costco',         'Willian', 28),
  ('bananas',            '1 bunch','not too ripe',     'Aldi',           'Aline',   26),
  ('greek yogurt',       '4',      '',                 'Aldi',           'Aline',   26),
  ('sourdough',          '1',      '',                 'Aldi',           'Willian', 20),
  ('dish soap',          '',       '',                 'Walmart',        'Willian', 14),
  ('aa batteries',       '1 pack', 'for the clock',    'Walmart',        'Aline',   12),
  ('strawberries',       '2 lb',   'if they look good','Farmers Market', 'Aline',    8),
  ('basil',              '1',      '',                 'Farmers Market', 'Aline',    8),
  ('rice noodles',       '2',      'flat, not thin',   'Asian Market',   'Willian',  5),
  ('sunscreen',          '',       'anywhere works',   null,             'Willian',  3)
) as v(item, qty, note, store, who, age)
join items i on i.name_norm = v.item;

-- Bought earlier today, so the un-buy strip has something in it.
insert into entries (item_id, qty, planned_store, bought_store, added_by, added_at, done_at)
select i.id, v.qty,
       (select id from stores where name = v.planned),
       (select id from stores where name = v.bought),
       v.who, now() - interval '9 hours', now() - (v.ago || ' hours')::interval
from (values
  ('milk',         '2',  'Aldi',   'Aldi',   'Aline',   4),
  ('coffee beans', '1',  'Costco', 'Aldi',   'Willian', 4)
) as v(item, qty, planned, bought, who, ago)
join items i on i.name_norm = v.item;

-- History, so the usuals row (bought three or more times in sixty days, not
-- currently on the list) has something to offer as a one-tap restock.
insert into entries (item_id, qty, planned_store, bought_store, added_by, added_at, done_at)
select i.id, '1',
       (select id from stores where name = v.store),
       (select id from stores where name = v.store),
       v.who,
       now() - ((v.weeks * 7) || ' days')::interval,
       now() - ((v.weeks * 7 - 1) || ' days')::interval
from (values
  ('milk',         'Aldi',   'Aline',   1),
  ('milk',         'Aldi',   'Willian', 2),
  ('milk',         'Aldi',   'Aline',   3),
  ('eggs',         'Aldi',   'Willian', 1),
  ('eggs',         'Aldi',   'Aline',   2),
  ('eggs',         'Aldi',   'Willian', 4),
  ('coffee beans', 'Costco', 'Willian', 2),
  ('coffee beans', 'Costco', 'Willian', 5),
  ('coffee beans', 'Costco', 'Aline',   7),
  ('sourdough',    'Aldi',   'Aline',   2),
  ('sourdough',    'Aldi',   'Willian', 6)
) as v(item, store, who, weeks)
join items i on i.name_norm = v.item;

commit;
