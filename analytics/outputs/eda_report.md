# EDA Report

## Raw shape

`(891, 15)`

## `df.info()`

```text
<class 'pandas.core.frame.DataFrame'>
RangeIndex: 891 entries, 0 to 890
Data columns (total 15 columns):
 #   Column       Non-Null Count  Dtype  
---  ------       --------------  -----  
 0   survived     891 non-null    int64  
 1   pclass       891 non-null    int64  
 2   sex          891 non-null    object 
 3   age          714 non-null    float64
 4   sibsp        891 non-null    int64  
 5   parch        891 non-null    int64  
 6   fare         891 non-null    float64
 7   embarked     889 non-null    object 
 8   class        891 non-null    object 
 9   who          891 non-null    object 
 10  adult_male   891 non-null    bool   
 11  deck         204 non-null    object 
 12  embark_town  889 non-null    object 
 13  alive        891 non-null    object 
 14  alone        891 non-null    bool   
dtypes: bool(2), float64(2), int64(4), object(7)
memory usage: 92.4+ KB
```

## `df.describe()`

          survived      pclass   sex         age       sibsp       parch        fare embarked  class  who adult_male deck  embark_town alive alone
count   891.000000  891.000000   891  714.000000  891.000000  891.000000  891.000000      889    891  891        891  204          889   891   891
unique         NaN         NaN     2         NaN         NaN         NaN         NaN        3      3    4          2    8            3     2     2
top            NaN         NaN  male         NaN         NaN         NaN         NaN        s  Third  man      False    C  Southampton    no  True
freq           NaN         NaN   577         NaN         NaN         NaN         NaN      644    491  537        478   59          644   549   537
mean      0.383838    2.308642   NaN   29.699118    0.523008    0.381594   32.204208      NaN    NaN  NaN        NaN  NaN          NaN   NaN   NaN
std       0.486592    0.836071   NaN   14.526497    1.102743    0.806057   49.693429      NaN    NaN  NaN        NaN  NaN          NaN   NaN   NaN
min       0.000000    1.000000   NaN    0.420000    0.000000    0.000000    0.000000      NaN    NaN  NaN        NaN  NaN          NaN   NaN   NaN
25%       0.000000    2.000000   NaN   20.125000    0.000000    0.000000    7.910400      NaN    NaN  NaN        NaN  NaN          NaN   NaN   NaN
50%       0.000000    3.000000   NaN   28.000000    0.000000    0.000000   14.454200      NaN    NaN  NaN        NaN  NaN          NaN   NaN   NaN
75%       1.000000    3.000000   NaN   38.000000    1.000000    0.000000   31.000000      NaN    NaN  NaN        NaN  NaN          NaN   NaN   NaN
max       1.000000    3.000000   NaN   80.000000    8.000000    6.000000  512.329200      NaN    NaN  NaN        NaN  NaN          NaN   NaN   NaN

## Missing values

|             |   missing_pct |
|:------------|--------------:|
| deck        |         77.1  |
| age         |         19.87 |
| embarked    |          0.22 |
| embark_town |          0.22 |

## Cleaning decisions

- `deck`: 77.10% missing (>30%); retained it with an explicit `Missing` category because dropping the feature would discard a potentially useful cabin-location signal while direct imputation would be misleading.
- `age`: 19.87% missing (5–30%), so imputed with median.
- `embarked`: 0.22% missing (<5%), so dropped affected rows (2 rows).
- `embark_town`: 0.22% missing (<5%), so dropped affected rows (0 rows).

Cleaned shape: `(889, 15)`

## Univariate results

- Age IQR bounds: [2.500, 54.500], outliers: **65**.
- Fare IQR bounds: [-26.761, 65.656], outliers: **114**.
- Fare mean: **32.0967**; median: **14.4542**; mode: **8.0500**.
- By the mean/median/mode ordering, fare is **right-skewed**.

## Survival rates

### By sex

|        |   survival_rate_pct |
|:-------|--------------------:|
| female |               74.04 |
| male   |               18.89 |

### By pclass

|    |   survival_rate_pct |
|---:|--------------------:|
|  1 |               62.62 |
|  2 |               47.28 |
|  3 |               24.24 |

### By sex and pclass

| sex    |   pclass |   survival_rate_pct |
|:-------|---------:|--------------------:|
| female |        1 |               96.74 |
| female |        2 |               92.11 |
| female |        3 |               50    |
| male   |        1 |               36.89 |
| male   |        2 |               15.74 |
| male   |        3 |               13.54 |

## Exact six-column correlation matrix

|          |   survived |   pclass |     age |   sibsp |   parch |    fare |
|:---------|-----------:|---------:|--------:|--------:|--------:|--------:|
| survived |     1      |  -0.3355 | -0.0698 | -0.034  |  0.0832 |  0.2553 |
| pclass   |    -0.3355 |   1      | -0.3365 |  0.0817 |  0.0168 | -0.5482 |
| age      |    -0.0698 |  -0.3365 |  1      | -0.2325 | -0.1715 |  0.0937 |
| sibsp    |    -0.034  |   0.0817 | -0.2325 |  1      |  0.4145 |  0.1609 |
| parch    |     0.0832 |   0.0168 | -0.1715 |  0.4145 |  1      |  0.2175 |
| fare     |     0.2553 |  -0.5482 |  0.0937 |  0.1609 |  0.2175 |  1      |

### Two strongest absolute off-diagonal correlations

- `pclass` vs `fare`: r = -0.5482 (|r| = 0.5482).
- `sibsp` vs `parch`: r = 0.4145 (|r| = 0.4145).

## Chart interpretation 1 — survival by class and sex

Women have substantially higher survival rates than men in every passenger class in the cleaned data, and first/second-class passengers have higher survival rates than third-class passengers within each sex. The separation by both variables shows that survival is associated with their combination rather than with either feature alone.

## Chart interpretation 2 — fare, class, and survival

Fare is much higher and more dispersed in the upper passenger classes, while survivors generally occupy higher-fare portions of the class-specific distributions. Because fare and class are strongly related, the chart supports an economic-position pattern without treating fare as an independent explanation of survival.

## Chart interpretation 3 — age, fare, sex, and survival

The points show substantial overlap, but survival outcomes are not distributed uniformly across age, fare, and sex. Combining the variables in one view reinforces the earlier pattern that demographic and economic factors jointly describe survival better than any single variable alone.

## Chart interpretation 4 — class and embarkation

Survival rates still differ strongly by passenger class after separating the observations by embarkation port. Port-level differences should be read in the context of class composition, so this chart adds context to the main class pattern rather than establishing a causal effect of embarkation.

## Exploratory standardization check

|      |   before_mean |   before_std |   after_mean |   after_std |
|:-----|--------------:|-------------:|-------------:|------------:|
| age  |       29.3152 |      12.9776 |            0 |           1 |
| fare |       32.0967 |      49.6695 |            0 |           1 |

The transformed age and fare columns are approximately mean 0 and standard deviation 1. This is an EDA sanity check only; the modeling script fits its own preprocessing exclusively on the training split.