begin;
create extension if not exists pgtap with schema extensions;
select plan(7);

select has_table('public', 'usage_counters', 'usage_counters exists');
select has_column('public', 'gate_events', 'replied', 'gate_events tracks replies');
select is((select paused from public.app_settings), false, 'not paused by default');
select is((select invite_max_failed_attempts from public.app_settings), 5, 'invites lock after 5 wrong codes');
select ok('capped' = any(enum_range(null::public.gate_decision)::text[]), 'gate_decision has capped');
select throws_ok(
  $$ insert into public.usage_counters (user_id, day, kind) values (gen_random_uuid(), current_date, 'sms') $$,
  '23514', null, 'usage kind is constrained');

set local role anon;
select is((select count(*)::int from public.usage_counters), 0, 'anon cannot read usage');
reset role;

select * from finish();
rollback;
