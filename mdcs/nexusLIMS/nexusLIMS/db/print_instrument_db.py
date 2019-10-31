from nexusLIMS import instruments

with open('instruments.csv', 'w') as f:
    for k,v in instruments.instrument_db.items():
        print(f'{v.name},{v.api_url},{v.calendar_name},{v.calendar_url},'
              f'{v.location},{v.schema_name},{v.property_tag},'
              f'{v.filestore_path}',
              file=f)
