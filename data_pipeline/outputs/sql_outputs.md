# SQL Query Evidence

Fixed conversion rate: **1 GBP = 105.50 INR**

## 1. SELECT/WHERE

```sql
SELECT title, price_gbp, rating FROM books WHERE rating >= 4 ORDER BY rating DESC;
```

| title                                                                    |   price_gbp |   rating |
|:-------------------------------------------------------------------------|------------:|---------:|
| 1,000 Places to See Before You Die                                       |       26.08 |        5 |
| A Time of Torment (Charlie Parker #14)                                   |       48.35 |        5 |
| What Happened on Beale Street (Secrets of the South Mysteries #2)        |       25.37 |        5 |
| The Bachelor Girl's Guide to Murder (Herringford and Watts Mysteries #1) |       52.3  |        5 |
| The Silkworm (Cormoran Strike #2)                                        |       23.05 |        5 |
| The Girl You Lost                                                        |       12.29 |        5 |
| A Flight of Arrows (The Pathfinders #2)                                  |       55.53 |        5 |
| Mrs. Houdini                                                             |       30.25 |        5 |
| The Passion of Dolssa                                                    |       28.32 |        5 |
| Voyager (Outlander #3)                                                   |       21.07 |        5 |
| The Red Tent                                                             |       35.66 |        5 |
| Between Shades of Gray                                                   |       20.79 |        5 |
| While You Were Mine                                                      |       41.32 |        5 |
| A Spy's Devotion (The Regency Spies of London #1)                        |       16.97 |        5 |
| Full Moon over Noah’s Ark: An Odyssey to Mount Ararat and Beyond         |       49.43 |        4 |
| A Year in Provence (Provence #1)                                         |       56.88 |        4 |
| Sharp Objects                                                            |       47.82 |        4 |
| The Past Never Ends                                                      |       56.5  |        4 |
| The Murder of Roger Ackroyd (Hercule Poirot #4)                          |       44.1  |        4 |
| Murder at the 42nd Street Library (Raymond Ambler #1)                    |       54.36 |        4 |
| Delivering the Truth (Quaker Midwife Mystery #1)                         |       20.89 |        4 |
| The Mysterious Affair at Styles (Hercule Poirot #1)                      |       24.8  |        4 |
| The No. 1 Ladies' Detective Agency (No. 1 Ladies' Detective Agency #1)   |       57.7  |        4 |
| The Marriage of Opposites                                                |       28.08 |        4 |
| A Paris Apartment                                                        |       39.01 |        4 |
| World Without End (The Pillars of the Earth #2)                          |       32.97 |        4 |
| Lost Among the Living                                                    |       27.7  |        4 |

## 2. ORDER BY

```sql
SELECT title, price_inr FROM books ORDER BY price_inr DESC LIMIT 10;
```

| title                                                                  |   price_inr |
|:-----------------------------------------------------------------------|------------:|
| Boar Island (Anna Pigeon #19)                                          |     6275.14 |
| The No. 1 Ladies' Detective Agency (No. 1 Ladies' Detective Agency #1) |     6087.35 |
| A Year in Provence (Provence #1)                                       |     6000.84 |
| The Past Never Ends                                                    |     5960.75 |
| The Last Painting of Sara de Vos                                       |     5860.52 |
| A Flight of Arrows (The Pathfinders #2)                                |     5858.42 |
| Murder at the 42nd Street Library (Raymond Ambler #1)                  |     5734.98 |
| The Last Mile (Amos Decker #2)                                         |     5719.16 |
| 1st to Die (Women's Murder Club #1)                                    |     5694.89 |
| Tipping the Velvet                                                     |     5669.57 |

## 3. LIMIT

```sql
SELECT title, rating FROM books LIMIT 5;
```

| title                                                               |   rating |
|:--------------------------------------------------------------------|---------:|
| It's Only the Himalayas                                             |        2 |
| Full Moon over Noah’s Ark: An Odyssey to Mount Ararat and Beyond    |        4 |
| See America: A Celebration of Our National Parks & Treasured Sites  |        3 |
| Vagabonding: An Uncommon Guide to the Art of Long-Term World Travel |        2 |
| Under the Tuscan Sun                                                |        3 |

## 4. DISTINCT

```sql
SELECT DISTINCT category_name FROM categories ORDER BY category_name;
```

| category_name      |
|:-------------------|
| Historical Fiction |
| Mystery            |
| Travel             |

## 5. IN

```sql
SELECT title, category_id FROM books WHERE category_id IN (1, 2, 3) ORDER BY category_id, title LIMIT 15;
```

| title                                                                     |   category_id |
|:--------------------------------------------------------------------------|--------------:|
| A Flight of Arrows (The Pathfinders #2)                                   |             1 |
| A Paris Apartment                                                         |             1 |
| A Spy's Devotion (The Regency Spies of London #1)                         |             1 |
| Between Shades of Gray                                                    |             1 |
| Forever and Forever: The Courtship of Henry Longfellow and Fanny Appleton |             1 |
| Girl With a Pearl Earring                                                 |             1 |
| Girl in the Blue Coat                                                     |             1 |
| Glory over Everything: Beyond The Kitchen House                           |             1 |
| Lilac Girls                                                               |             1 |
| Lost Among the Living                                                     |             1 |
| Love, Lies and Spies                                                      |             1 |
| Mrs. Houdini                                                              |             1 |
| Starlark                                                                  |             1 |
| The Constant Princess (The Tudor Court #1)                                |             1 |
| The Guernsey Literary and Potato Peel Pie Society                         |             1 |

## 6. JOIN

```sql
SELECT c.category_name, b.title, b.rating, b.price_inr FROM books b JOIN categories c ON b.category_id = c.category_id ORDER BY b.rating DESC, c.category_name, b.title LIMIT 10;
```

| category_name      | title                                                                    |   rating |   price_inr |
|:-------------------|:-------------------------------------------------------------------------|---------:|------------:|
| Historical Fiction | A Flight of Arrows (The Pathfinders #2)                                  |        5 |     5858.42 |
| Historical Fiction | A Spy's Devotion (The Regency Spies of London #1)                        |        5 |     1790.33 |
| Historical Fiction | Between Shades of Gray                                                   |        5 |     2193.34 |
| Historical Fiction | Mrs. Houdini                                                             |        5 |     3191.38 |
| Historical Fiction | The Passion of Dolssa                                                    |        5 |     2987.76 |
| Historical Fiction | The Red Tent                                                             |        5 |     3762.13 |
| Historical Fiction | Voyager (Outlander #3)                                                   |        5 |     2222.89 |
| Historical Fiction | While You Were Mine                                                      |        5 |     4359.26 |
| Mystery            | A Time of Torment (Charlie Parker #14)                                   |        5 |     5100.92 |
| Mystery            | The Bachelor Girl's Guide to Murder (Herringford and Watts Mysteries #1) |        5 |     5517.65 |

## pandas equivalence check

### `pd.read_sql(...)` JOIN result
| category_name      | title                                                                    |   rating |   price_inr |
|:-------------------|:-------------------------------------------------------------------------|---------:|------------:|
| Historical Fiction | A Flight of Arrows (The Pathfinders #2)                                  |        5 |     5858.42 |
| Historical Fiction | A Spy's Devotion (The Regency Spies of London #1)                        |        5 |     1790.33 |
| Historical Fiction | Between Shades of Gray                                                   |        5 |     2193.34 |
| Historical Fiction | Mrs. Houdini                                                             |        5 |     3191.38 |
| Historical Fiction | The Passion of Dolssa                                                    |        5 |     2987.76 |
| Historical Fiction | The Red Tent                                                             |        5 |     3762.13 |
| Historical Fiction | Voyager (Outlander #3)                                                   |        5 |     2222.89 |
| Historical Fiction | While You Were Mine                                                      |        5 |     4359.26 |
| Mystery            | A Time of Torment (Charlie Parker #14)                                   |        5 |     5100.92 |
| Mystery            | The Bachelor Girl's Guide to Murder (Herringford and Watts Mysteries #1) |        5 |     5517.65 |

### `pd.merge(...)` JOIN result
| category_name      | title                                                                    |   rating |   price_inr |
|:-------------------|:-------------------------------------------------------------------------|---------:|------------:|
| Historical Fiction | A Flight of Arrows (The Pathfinders #2)                                  |        5 |     5858.42 |
| Historical Fiction | A Spy's Devotion (The Regency Spies of London #1)                        |        5 |     1790.33 |
| Historical Fiction | Between Shades of Gray                                                   |        5 |     2193.34 |
| Historical Fiction | Mrs. Houdini                                                             |        5 |     3191.38 |
| Historical Fiction | The Passion of Dolssa                                                    |        5 |     2987.76 |
| Historical Fiction | The Red Tent                                                             |        5 |     3762.13 |
| Historical Fiction | Voyager (Outlander #3)                                                   |        5 |     2222.89 |
| Historical Fiction | While You Were Mine                                                      |        5 |     4359.26 |
| Mystery            | A Time of Torment (Charlie Parker #14)                                   |        5 |     5100.92 |
| Mystery            | The Bachelor Girl's Guide to Murder (Herringford and Watts Mysteries #1) |        5 |     5517.65 |

**Equivalent:** `True`

### Second `pd.read_sql(...)` result
| title                                                                    |   price_gbp |   rating |
|:-------------------------------------------------------------------------|------------:|---------:|
| 1,000 Places to See Before You Die                                       |       26.08 |        5 |
| A Time of Torment (Charlie Parker #14)                                   |       48.35 |        5 |
| What Happened on Beale Street (Secrets of the South Mysteries #2)        |       25.37 |        5 |
| The Bachelor Girl's Guide to Murder (Herringford and Watts Mysteries #1) |       52.3  |        5 |
| The Silkworm (Cormoran Strike #2)                                        |       23.05 |        5 |
| The Girl You Lost                                                        |       12.29 |        5 |
| A Flight of Arrows (The Pathfinders #2)                                  |       55.53 |        5 |
| Mrs. Houdini                                                             |       30.25 |        5 |
| The Passion of Dolssa                                                    |       28.32 |        5 |
| Voyager (Outlander #3)                                                   |       21.07 |        5 |
