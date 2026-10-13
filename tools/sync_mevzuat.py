import requests, json

SB = 'https://igtzrydpnglnvwzgvcym.supabase.co'
KEY = 'sb_publishable_0naUfbqTqp5V-8Ca29VDlw_SgGwIasx'
headers = {
    'apikey': KEY,
    'Authorization': f'Bearer {KEY}',
    'Content-Type': 'application/json',
    'Prefer': 'resolution=merge-duplicates, return=representation'
}

resp = requests.get(f'{SB}/rest/v1/depo?id=eq.mevzuat&select=veri', headers=headers)
resp.raise_for_status()
sb_veri = resp.json()[0]['veri']

with open('data/mevzuat.json', 'r', encoding='utf-8') as f:
    lokal_veri = json.load(f)

for sb_tur in sb_veri.get('turler', []):
    lokal_tur = next((t for t in lokal_veri['turler'] if t['id'] == sb_tur['id']), None)
    if not lokal_tur:
        lokal_veri['turler'].append(sb_tur)
        continue
    for sb_mev in sb_tur.get('mevzuat', []):
        lokal_mev = next((m for m in lokal_tur['mevzuat'] if m['id'] == sb_mev['id']), None)
        if not lokal_mev:
            lokal_tur['mevzuat'].append(sb_mev)
            continue
        lokal_maddeler = {a['no']: a for a in lokal_mev.get('maddeler', [])}
        for sb_madde in sb_mev.get('maddeler', []):
            no = sb_madde['no']
            if no not in lokal_maddeler:
                lokal_mev['maddeler'].append(sb_madde)
                print(f"Eklendi (SB -> Lokal): {sb_tur['id']} {sb_mev['id']} m.{no}")
            else:
                lok_art = lokal_maddeler[no]
                if (not lok_art.get('paragraf')) and sb_madde.get('paragraf'):
                    lok_art['paragraf'] = sb_madde['paragraf']
                    lok_art['baslik'] = sb_madde.get('baslik', lok_art.get('baslik'))
                    print(f"Guncellendi (SB -> Lokal): {sb_tur['id']} {sb_mev['id']} m.{no}")

with open('data/mevzuat.json', 'w', encoding='utf-8') as f:
    json.dump(lokal_veri, f, ensure_ascii=False, indent=2)

payload = {'id': 'mevzuat', 'veri': lokal_veri}
post_resp = requests.post(f'{SB}/rest/v1/depo', headers=headers, json=payload)
print('Supabase status:', post_resp.status_code)
print('Senkronizasyon tamamlandı.')
