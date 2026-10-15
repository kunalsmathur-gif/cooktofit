begin;
create extension if not exists pgtap with schema extensions;
select plan(20);

select has_table('public', 'households', 'households exists');
select has_table('public', 'users', 'users exists');
select has_table('public', 'channel_identities', 'channel_identities exists');
select has_table('public', 'access_list', 'access_list exists');
select has_table('public', 'gate_events', 'gate_events exists');
select has_table('public', 'waitlist', 'waitlist exists');
select has_table('public', 'app_settings', 'app_settings exists');

select is(
  (select count(*)::int from pg_tables where schemaname = 'public' and not rowsecurity),
  0, 'every public table has RLS enabled');

select is((select gate_mode::text from public.app_settings), 'invite_only', 'gate defaults to invite_only');
select is((select non_member_reply::text from public.app_settings), 'silent', 'non-members get silence by default');
select is((select invites_per_member from public.app_settings), 0, 'members cannot invite before launch');

select throws_ok($$ insert into public.app_settings (id) values (2) $$, '23514', null, 'app_settings is a singleton');
select throws_ok($$ insert into public.access_list (phone_e164, display_name) values ('9876543210', 'x') $$,
  '23514', null, 'phone must be E.164');
select lives_ok($$ insert into public.access_list (phone_e164, display_name) values ('+919876543210', 'Test') $$,
  'valid invite row');
select throws_ok($$ update public.access_list set status = 'active' where phone_e164 = '+919876543210' $$,
  '23514', null, 'active requires a linked user and activated_at');
select throws_ok($$ update public.access_list set status = 'revoked' where phone_e164 = '+919876543210' $$,
  '23514', null, 'revoked requires revoked_at');

-- anon sees nothing
set local role anon;
select is((select count(*)::int from public.access_list), 0, 'anon cannot read access_list');
select is((select count(*)::int from public.app_settings), 0, 'anon cannot read app_settings');
reset role;

-- authenticated non-admin sees nothing in admin tables
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-000000000001","role":"authenticated"}', true);
select is((select count(*)::int from public.access_list), 0, 'non-admin cannot read access_list');
select is(public.is_admin(), false, 'unknown auth user is not admin');
reset role;

select * from finish();
rollback;
