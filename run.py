#! /usr/bin/env python

import xmlrpc.client
import concurrent.futures
import time
import sys

url = 'https://odoo-duckrabbit-odoo16-duckrabbit-staging-14682276.dev.odoo.com'
db = 'odoo-duckrabbit-odoo16-duckrabbit-staging-14682276'
username = 'mikilio@duckrabbit.com'
password = 'f28a37b47cc5845cedcf73a43e8272b29f485d74'

area = 'S2S'
shelves = ['1','2','3','4']
sections = ['A','B','C']
etages = ['N1','N2','N3','N4','N5','N6','N7']
location = ['01','02','03','04','05','06','07','08']


def main():

    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    print(common.version())
    uid = common.authenticate(db, username, password, {})
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    probe = models.execute_kw(
        db, uid, password,
        'stock.location',
        'search_read', [
            [('name','like',f'{area}%')],
        ],
        {'fields': ['complete_name', 'location_id'], 'limit': 1}
    )

    path = probe[0]['complete_name'].rpartition('/')[0]

    print(path)


    def get_records():
        return models.execute_kw(
            db, uid, password,
            'stock.location',
            'search_read', [
                [('name','like',f'{area}%')],
            ],
            {'fields': ['name', 'barcode']}
        )

    wanted_locations = []

    for a in shelves:
        for b in sections:
            for c in etages:
                for d in location:
                    wanted_locations.append(f"S2S-{a}-{b}-{c}-{d}")

    def create_location(name):
        return models.execute_kw(
            db, uid, password,
            'stock.location',
            'name_create',
            [path + '/' + name]
        )

    with concurrent.futures.ThreadPoolExecutor() as executor:
        while True:
            existing_locations = [record['name'] for record in get_records() ]
            to_create = [name for name in wanted_locations if name not in existing_locations ]

            if not to_create:
                break

            print(f'Will create locations:\n{to_create}')

            futures = {executor.submit(create_location, name): name for name in to_create}

            for future in concurrent.futures.as_completed(futures):
                name = futures[future]
                try:
                    result = future.result()
                    print(f"{name} created successfully with result: {result}")
                except Exception as exc:
                    print(f"{name} generated an exception: {exc}",file=sys.stderr)


            time.sleep(1)


    def update_barcode(record):
        print(record)
        return models.execute_kw(
            db, uid, password,
            'stock.location',
            'write',
            [
                [record['id']],
                {'barcode': record['name']}
            ]
        )
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        while True:
            wrong_barcode_locations = [record for record in get_records() if record['name'] != record['barcode']]

            if not wrong_barcode_locations:
                break

            print(f'Updating Barcodes for:\n{to_create}')

            futures = {executor.submit(update_barcode, record): record for record in wrong_barcode_locations}

            for future in concurrent.futures.as_completed(futures):
                name = futures[future]
                try:
                    result = future.result()
                    print(f"{name} updated successfully with result: {result}")
                except Exception as exc:
                    print(f"{name} generated an exception: {exc}",file=sys.stderr)

            time.sleep(1)

if __name__ == '__main__':
    main()
