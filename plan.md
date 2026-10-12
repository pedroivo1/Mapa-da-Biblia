# Plano 2: o que você faz no Supabase, no Google e na Vercel

## A. Supabase

1. Crie o projeto em [supabase.com](https://supabase.com), região South America (São Paulo). Guarde a senha do banco.
2. Em **SQL Editor**, rode:

```sql
create table public.progresso (
  user_id uuid primary key references auth.users(id) on delete cascade,
  lido jsonb not null default '{}'::jsonb,
  versiculos jsonb not null default '{}'::jsonb,
  atualizado_em timestamptz not null default now()
);

alter table public.progresso enable row level security;

create policy "ler o próprio progresso"
  on public.progresso for select to authenticated
  using ((select auth.uid()) = user_id);

create policy "criar o próprio progresso"
  on public.progresso for insert to authenticated
  with check ((select auth.uid()) = user_id);

create policy "editar o próprio progresso"
  on public.progresso for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);
```

3. Em **Authentication → Sign In / Providers → Email**: deixe ativado, com "Confirm email" ligado e senha mínima de 8 caracteres.
4. Em **Authentication → URL Configuration**:
   - **Site URL:** `https://SEU-DOMINIO.vercel.app`. Preencha depois do primeiro deploy.
   - **Redirect URLs:** `https://SEU-DOMINIO.vercel.app/**`, `http://localhost:8000/**` e, para os previews, `https://*-SEU-TIME.vercel.app/**`.
5. Em **Authentication → Emails**: o SMTP embutido envia pouquíssimos e-mails por hora e serve só para testes. Para uso real, configure um SMTP próprio (por exemplo Resend ou Brevo, que têm plano grátis). Traduza os modelos de "Confirm signup" e "Reset password" para português.
6. Em **Project Settings → API Keys**: copie a Project URL e a publishable key para `js/config.js`. Nunca use a secret/service_role.
7. Rode **Advisors → Security** e confirme que não há aviso de RLS.

## B. Google Cloud (login com Google)

1. Em [console.cloud.google.com](https://console.cloud.google.com), crie um projeto.
2. Em **Google Auth Platform → Branding** (tela de consentimento):
   - Tipo "External", com nome do app, e-mail de suporte e logo opcional.
   - Link da página inicial e de `privacidade.html`.
   - **Authorized domains:** seu domínio da Vercel e `SEU-REF.supabase.co`.
3. Em **Data Access**: use só o escopo `openid`.
4. No cliente OAuth:
   - **Authorized JavaScript origins:** `https://SEU-DOMINIO.vercel.app` e `http://localhost:8000`.
   - **Authorized redirect URI:** `https://SEU-REF.supabase.co/auth/v1/callback`. Esse endereço aparece copiável na tela do provedor Google no Supabase.
5. Copie o Client ID e o Client Secret para **Supabase → Authentication → Providers → Google** e ative.
6. Em **Audience → Publish app**: mude para "In production". Em "Testing", só os e-mails de teste conseguem entrar.

## C. Vercel

1. Suba o repositório para o GitHub: `gh repo create mapa-da-biblia --private --source . --push`.
2. Em [vercel.com](https://vercel.com), use **Add New → Project → Import**:
   - **Framework Preset:** Other.
   - **Build Command:** vazio.
   - **Output Directory:** `.` (raiz).
   - Não há variáveis de ambiente, porque a configuração pública está em `js/config.js`.
3. Depois do primeiro deploy, coloque a URL final no Supabase (A.4) e no Google (B.2 e B.4).
4. (Opcional) Em **Settings → Domains**, adicione um domínio próprio e repita a URL nas três telas.

## Verificação

1. Local: rode `python -m http.server` e abra `http://localhost:8000/biblia/` sem login. O mapa aparece, as caixas ficam desativadas e o convite para entrar aparece.
2. Em `entrar.html`, crie uma conta por e-mail, confirme pelo e-mail recebido e entre.
3. Marque capítulos. Na tabela `progresso` do Supabase (ou com `select * from progresso` pelo MCP), confirme a linha do seu `user_id`.
4. Recarregue a página e o progresso continua lá. Abra em outro navegador, entre e veja o mesmo progresso.
5. Saia: as caixas desativam. Entre com o Google e confirme que é uma conta separada, com progresso vazio.
6. Teste "Esqueci a senha" de ponta a ponta.
7. Teste o RLS: com a chave publicável e sem sessão, `select` em `progresso` devolve 0 linhas. Logado como A, não aparecem as linhas de B.
8. Importação: com progresso antigo no `localStorage`, o primeiro login sobe os dados e limpa as chaves locais.
9. Repita os passos 1 a 5 na URL da Vercel.
