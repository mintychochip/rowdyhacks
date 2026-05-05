import asyncio
from datetime import datetime, UTC
from app.database import async_session
from app.models import CrawledHackathon
from sqlalchemy import select

HISTORICAL_HACKATHONS = [
    ('https://hackmit2015.devpost.com', 'HackMIT 2015', '2015-09-19', '2015-09-20'),
    ('https://hackmit2016.devpost.com', 'HackMIT 2016', '2016-09-17', '2016-09-18'),
    ('https://hackmit2017.devpost.com', 'HackMIT 2017', '2017-09-16', '2017-09-17'),
    ('https://hackmit2018.devpost.com', 'HackMIT 2018', '2018-09-15', '2018-09-16'),
    ('https://hackmit2019.devpost.com', 'HackMIT 2019', '2019-09-14', '2019-09-15'),
    ('https://hackmit2020.devpost.com', 'HackMIT 2020', '2020-09-18', '2020-09-20'),
    ('https://hackmit2021.devpost.com', 'HackMIT 2021', '2021-09-17', '2021-09-19'),
    ('https://hackmit2022.devpost.com', 'HackMIT 2022', '2022-10-01', '2022-10-02'),
    ('https://calhacks2015.devpost.com', 'CalHacks 2015', '2015-10-09', '2015-10-11'),
    ('https://calhacks2016.devpost.com', 'CalHacks 2016', '2016-11-11', '2016-11-13'),
    ('https://calhacks2017.devpost.com', 'CalHacks 2017', '2017-10-06', '2017-10-08'),
    ('https://calhacks2018.devpost.com', 'CalHacks 2018', '2018-11-02', '2018-11-04'),
    ('https://calhacks2019.devpost.com', 'CalHacks 2019', '2019-10-25', '2019-10-27'),
    ('https://calhacks2020.devpost.com', 'CalHacks 2020', '2020-10-16', '2020-10-18'),
    ('https://calhacks2021.devpost.com', 'CalHacks 2021', '2021-10-22', '2021-10-24'),
    ('https://calhacks2022.devpost.com', 'CalHacks 2022', '2022-10-14', '2022-10-16'),
    ('https://pennappsxxii.devpost.com', 'PennApps XXII', '2021-03-19', '2021-03-21'),
    ('https://pennappsxxiii.devpost.com', 'PennApps XXIII', '2022-09-16', '2022-09-18'),
    ('https://treehacks2016.devpost.com', 'TreeHacks 2016', '2016-02-12', '2016-02-14'),
    ('https://treehacks2017.devpost.com', 'TreeHacks 2017', '2017-02-17', '2017-02-19'),
    ('https://treehacks2018.devpost.com', 'TreeHacks 2018', '2018-02-16', '2018-02-18'),
    ('https://treehacks2019.devpost.com', 'TreeHacks 2019', '2019-02-15', '2019-02-17'),
    ('https://treehacks2020.devpost.com', 'TreeHacks 2020', '2020-02-14', '2020-02-16'),
    ('https://treehacks2021.devpost.com', 'TreeHacks 2021', '2021-02-12', '2021-02-14'),
    ('https://treehacks2022.devpost.com', 'TreeHacks 2022', '2022-02-18', '2022-02-20'),
    ('https://treehacks2023.devpost.com', 'TreeHacks 2023', '2023-02-17', '2023-02-19'),
    ('https://mhacks2015.devpost.com', 'MHacks 2015', '2015-09-11', '2015-09-13'),
    ('https://mhacks2016.devpost.com', 'MHacks 2016', '2016-10-07', '2016-10-09'),
    ('https://mhacks2017.devpost.com', 'MHacks 2017', '2017-09-22', '2017-09-24'),
    ('https://mhacks2018.devpost.com', 'MHacks 2018', '2018-10-12', '2018-10-14'),
    ('https://mhacks2019.devpost.com', 'MHacks 2019', '2019-09-20', '2019-09-22'),
    ('https://mhacks2020.devpost.com', 'MHacks 2020', '2020-09-18', '2020-09-20'),
    ('https://mhacks2021.devpost.com', 'MHacks 2021', '2021-09-24', '2021-09-26'),
    ('https://mhacks2022.devpost.com', 'MHacks 2022', '2022-09-23', '2022-09-25'),
    ('https://mhacks2023.devpost.com', 'MHacks 2023', '2023-09-15', '2023-09-17'),
    ('https://hackduke2015.devpost.com', 'HackDuke 2015', '2015-11-21', '2015-11-22'),
    ('https://hackduke2016.devpost.com', 'HackDuke 2016', '2016-11-19', '2016-11-20'),
    ('https://hackduke2017.devpost.com', 'HackDuke 2017', '2017-10-28', '2017-10-29'),
    ('https://hackduke2018.devpost.com', 'HackDuke 2018', '2018-10-27', '2018-10-28'),
    ('https://hackduke2019.devpost.com', 'HackDuke 2019', '2019-11-02', '2019-11-03'),
    ('https://hackduke2020.devpost.com', 'HackDuke 2020', '2020-12-05', '2020-12-06'),
    ('https://hackduke2021.devpost.com', 'HackDuke 2021', '2021-10-23', '2021-10-24'),
    ('https://hackduke2022.devpost.com', 'HackDuke 2022', '2022-10-22', '2022-10-23'),
    ('https://hackgt2015.devpost.com', 'HackGT 2015', '2015-09-25', '2015-09-27'),
    ('https://hackgt2016.devpost.com', 'HackGT 2016', '2016-09-23', '2016-09-25'),
    ('https://hackgt2017.devpost.com', 'HackGT 2017', '2017-10-13', '2017-10-15'),
    ('https://hackgt2018.devpost.com', 'HackGT 2018', '2018-10-19', '2018-10-21'),
    ('https://hackgt2019.devpost.com', 'HackGT 2019', '2019-10-25', '2019-10-27'),
    ('https://hackgt2020.devpost.com', 'HackGT 2020', '2020-10-16', '2020-10-18'),
    ('https://hackgt2021.devpost.com', 'HackGT 2021', '2021-10-22', '2021-10-24'),
    ('https://hackgt2022.devpost.com', 'HackGT 2022', '2022-10-14', '2022-10-16'),
    ('https://hackgt2023.devpost.com', 'HackGT 2023', '2023-10-13', '2023-10-15'),
]

async def add_historical():
    async with async_session() as db:
        added = 0
        for url, name, start, end in HISTORICAL_HACKATHONS:
            result = await db.execute(select(CrawledHackathon).where(CrawledHackathon.devpost_url == url))
            if result.scalar_one_or_none():
                continue

            try:
                start_dt = datetime.strptime(start, '%Y-%m-%d').replace(tzinfo=UTC)
                end_dt = datetime.strptime(end, '%Y-%m-%d').replace(tzinfo=UTC)
            except:
                continue

            hk = CrawledHackathon(
                devpost_url=url,
                name=name,
                start_date=start_dt,
                end_date=end_dt,
            )
            db.add(hk)
            added += 1

        await db.commit()

        result = await db.execute(select(CrawledHackathon))
        total = len(result.scalars().all())

        print(f'Added {added} historical hackathons')
        print(f'Total hackathons: {total}')

if __name__ == '__main__':
    asyncio.run(add_historical())
