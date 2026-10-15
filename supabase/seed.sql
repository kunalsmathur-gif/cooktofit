-- Local development seed. Safe defaults only; no real phone numbers.
insert into public.app_settings (id) values (1) on conflict (id) do nothing;
