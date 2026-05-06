Website user kayıt olur → mailine 6 haneli kod gider → kullanıcı kodu girer → hesap aktif olur

Bu standartta yok, özel modül/custom geliştirme gerekir.

Odoo tarafında yapılacak mantık:

res.users veya res.partner üzerine:

email_verified
verification_code
verification_expire_date

alanları eklenir.

Kayıt sonrası:

kullanıcı pasif/portal beklemede tutulur
mail template ile kod gönderilir
/verify-email gibi controller yazılır
doğru kod girilirse kullanıcı aktif edilir