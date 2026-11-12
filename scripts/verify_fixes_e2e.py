import httpx
import time

BASE = 'http://127.0.0.1:8000'

def main():
    client = httpx.Client(base_url=BASE, timeout=20.0)

    # 1. Health check
    r = client.get('/api/health')
    print('1. Health check:', r.status_code, r.json())
    assert r.status_code == 200

    # 2. Login as existing test user
    login_res = client.post('/api/auth/login', json={'phone': '9876543210', 'password': 'DemoPass123!'})
    print('2. Login status:', login_res.status_code)
    assert login_res.status_code == 200, login_res.text
    token = login_res.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    # 3. Test Notifications
    notif_res = client.get('/api/notifications', headers=headers)
    print('3. Notifications GET status:', notif_res.status_code)
    assert notif_res.status_code == 200, notif_res.text
    notif_data = notif_res.json()
    print(f"   Total notifications: {notif_data['total']}, Unread count: {notif_data['unread_count']}")
    assert len(notif_data['items']) > 0
    first_id = notif_data['items'][0]['id']

    # Mark single read
    patch_res = client.patch(f'/api/notifications/{first_id}/read', headers=headers)
    print('   Mark read status:', patch_res.status_code, patch_res.json()['is_read'])
    assert patch_res.status_code == 200
    assert patch_res.json()['is_read'] is True

    # Mark all read
    all_res = client.post('/api/notifications/read-all', headers=headers)
    print('   Mark all read status:', all_res.status_code, all_res.json())
    assert all_res.status_code == 200

    # Verify unread is now 0
    notif_after = client.get('/api/notifications', headers=headers).json()
    print('   Unread after mark-all:', notif_after['unread_count'])
    assert notif_after['unread_count'] == 0

    # 4. Test Facilities Search with query, ownership, auto_expand, and distance ranking
    # Madurai coordinates: 9.9252, 78.1198
    fac_res = client.get(
        '/api/facilities/nearby',
        params={
            'latitude': 9.9252,
            'longitude': 78.1198,
            'radius_km': 50,
            'ownership': 'Government',
            'limit': 10
        },
        headers=headers
    )
    print('4. Facilities search (Madurai 50km Gov):', fac_res.status_code)
    assert fac_res.status_code == 200, fac_res.text
    fac_data = fac_res.json()
    print(f"   Total found: {fac_data['total']}, items returned: {len(fac_data['items'])}")
    distances = [item['distance_km'] for item in fac_data['items']]
    print('   Distances (must be ascending):', distances)
    assert distances == sorted(distances), 'Distances must be sorted ascending!'
    for item in fac_data['items'][:3]:
        print(f"   - {item['name']} | Type: {item['facility_type']} | Owner: {item['ownership']} | Dist: {item['distance_km']} km | Source: {item['source']}")

    # Search with query 'Hospital'
    hosp_res = client.get(
        '/api/facilities/nearby',
        params={
            'latitude': 9.9252,
            'longitude': 78.1198,
            'query': 'Hospital',
            'radius_km': 100,
            'limit': 5
        },
        headers=headers
    )
    print('   Hospital search query results:', len(hosp_res.json()['items']))
    for item in hosp_res.json()['items'][:3]:
        print(f"   - Hospital: {item['name']} | Type: {item['facility_type']} | Dist: {item['distance_km']} km")

    # Auto-expansion test: radius 0.5 km where 0 facilities exist
    exp_res = client.get(
        '/api/facilities/nearby',
        params={
            'latitude': 9.9252,
            'longitude': 78.1198,
            'radius_km': 0.5,
            'auto_expand': 'true',
            'limit': 5
        },
        headers=headers
    )
    exp_data = exp_res.json()
    print('   Auto-expansion test: initial 0.5km expanded to:', exp_data['radius_km'], 'km | Found:', exp_data['total'])
    assert exp_data['resolved_location']['is_expanded'] is True

    # 5. PIN Code search
    pin_res = client.get('/api/villages/search', params={'q': '637211'})
    print('5. PIN Code search (637211):', pin_res.status_code, [v['name'] for v in pin_res.json()['items'][:2]])
    assert len(pin_res.json()['items']) > 0

    # 6. Custom locality registration
    custom_res = client.post('/api/villages/custom', json={
        'name': 'Chitlapakkam East',
        'district': 'Chengalpattu',
        'state': 'Tamil Nadu',
        'pincode': '600064'
    })
    print('6. Custom Village Created:', custom_res.status_code, custom_res.json()['name'], 'Lat/Lon:', custom_res.json()['latitude'], custom_res.json()['longitude'])
    assert custom_res.status_code == 201
    custom_village_id = custom_res.json()['id']

    # 7. Register new user with this custom village
    new_phone = '9841' + str(int(time.time()))[-6:]
    reg_res = client.post('/api/auth/register', json={
        'name': 'Ramesh Kumar',
        'phone': new_phone,
        'password': 'Password@123',
        'village_id': custom_village_id,
        'date_of_birth': '1988-06-15',
        'preferred_language': 'ta',
        'consent_given': True
    })
    print('7. Register with custom village status:', reg_res.status_code)
    assert reg_res.status_code == 201

    # Login with new user
    new_login = client.post('/api/auth/login', json={'phone': new_phone, 'password': 'Password@123'}).json()
    new_token = new_login['access_token']
    new_headers = {'Authorization': f'Bearer {new_token}'}

    # Establish patient profile linked to custom village
    pat_res = client.post('/api/patients', headers=new_headers, json={
        'village_id': custom_village_id,
        'date_of_birth': '1988-06-15',
        'preferred_language': 'ta',
        'consent_given': True
    })
    print('7b. Establish patient profile status:', pat_res.status_code)
    assert pat_res.status_code == 201

    # Check nearby facilities using authenticated user profile location
    new_fac = client.get('/api/facilities/nearby', headers=new_headers).json()
    print('8. Resolved location from registered custom village:', new_fac['resolved_location']['label'])
    print(f"   Nearby facilities found: {new_fac['total']}, Closest: {new_fac['items'][0]['name']} ({new_fac['items'][0]['distance_km']} km)")
    assert new_fac['total'] > 0
    print('\n======================================================')
    print('ALL END-TO-END VERIFICATION CHECKS PASSED SUCCESSFULLY!')
    print('======================================================')

if __name__ == '__main__':
    main()
