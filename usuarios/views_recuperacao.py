from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from .models_recuperacao import TokenRecuperacaoSenha
from .forms_recuperacao import SolicitarRecuperacaoForm, NovaSenhaForm

Usuario = get_user_model()


@csrf_protect
@never_cache
def solicitar_recuperacao(request):
    if request.method == 'POST':
        form = SolicitarRecuperacaoForm(request.POST)
        
        if form.is_valid():
            usuario = form.usuario_encontrado
            
            if usuario:
                token = TokenRecuperacaoSenha.objects.create(
                    usuario=usuario,
                    ip_solicitacao=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                # TODO: Integrar com sistema de e-mail do Marcos
                # Por enquanto, exibe o link no console (desenvolvimento)
                link_recuperacao = request.build_absolute_uri(
                    f'/usuarios/recuperar-senha/{token.token}/'
                )
                
                print(f"\n{'='*60}")
                print(f"LINK DE RECUPERAÇÃO DE SENHA (Ambiente de Desenvolvimento)")
                print(f"{'='*60}")
                print(f"Usuário: {usuario.email}")
                print(f"Token: {token.token}")
                print(f"Expira em: {token.expira_em}")
                print(f"Link: {link_recuperacao}")
                print(f"{'='*60}\n")
                
                # Marcos - Aqui você integrará com o sistema de logs
                # registrar_evento_recuperacao_senha(
                #     email=usuario.email,
                #     evento='solicitacao',
                #     sucesso=True,
                #     ip_address=request.META.get('REMOTE_ADDR')
                # )

            messages.success(
                request,
                'Se o e-mail informado estiver cadastrado no sistema, '
                'você receberá um link para recuperação de senha.'
            )
            return redirect('usuarios:solicitar_recuperacao')
    else:
        form = SolicitarRecuperacaoForm()
    
    context = {'form': form}
    return render(request, 'usuarios/solicitar_recuperacao.html', context)


@csrf_protect
@never_cache
def confirmar_recuperacao(request, token):
 
    try:
        token_obj = TokenRecuperacaoSenha.objects.get(token=token)
    except TokenRecuperacaoSenha.DoesNotExist:
        messages.error(
            request,
            'Link de recuperação inválido ou expirado. '
            'Por favor, solicite um novo link.'
        )
        return redirect('usuarios:solicitar_recuperacao')
    
    if not token_obj.is_valido():
        messages.error(
            request,
            'Link de recuperação inválido ou expirado. '
            'Por favor, solicite um novo link.'
        )
        return redirect('usuarios:solicitar_recuperacao')
    
    if request.method == 'POST':
        form = NovaSenhaForm(request.POST)
        
        if form.is_valid():
            # Atualiza a senha do usuário
            usuario = token_obj.usuario
            usuario.set_password(form.cleaned_data['senha1'])
            usuario.save()
            
            # Invalida o token após uso bem-sucedido (RS 2.4)
            token_obj.marcar_como_utilizado()
            
            # Marcos - Registrar sucesso no log
            # registrar_evento_recuperacao_senha(
            #     email=usuario.email,
            #     evento='senha_alterada',
            #     sucesso=True,
            #     ip_address=request.META.get('REMOTE_ADDR')
            # )
            
            messages.success(
                request,
                'Senha alterada com sucesso! Você já pode fazer login com a nova senha.'
            )
            return redirect('account_login')
    else:
        form = NovaSenhaForm()
    
    context = {
        'form': form,
        'token': token,
        'expira_em': token_obj.expira_em
    }
    return render(request, 'usuarios/confirmar_recuperacao.html', context)