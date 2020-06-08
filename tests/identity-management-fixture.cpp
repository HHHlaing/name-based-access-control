/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Copyright (c) 2014-2020, Regents of the University of California
 *
 * NAC library is free software: you can redistribute it and/or modify it under the
 * terms of the GNU Lesser General Public License as published by the Free Software
 * Foundation, either version 3 of the License, or (at your option) any later version.
 *
 * NAC library is distributed in the hope that it will be useful, but WITHOUT ANY
 * WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
 * PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more details.
 *
 * You should have received copies of the GNU General Public License and GNU Lesser
 * General Public License along with ndn-cxx, e.g., in COPYING.md file.  If not, see
 * <http://www.gnu.org/licenses/>.
 *
 * See AUTHORS.md for complete list of NAC library authors and contributors.
 */

#include "identity-management-fixture.hpp"

#include <ndn-cxx/util/io.hpp>
#include <ndn-cxx/security/additional-description.hpp>

#include <boost/filesystem.hpp>

namespace ndn {
namespace nac {
namespace tests {

IdentityManagementFixture::IdentityManagementFixture()
  : m_keyChain("pib-memory:", "tpm-memory:")
{
}

IdentityManagementFixture::~IdentityManagementFixture()
{
  boost::system::error_code ec;
  for (const auto& certFile : m_certFiles) {
    boost::filesystem::remove(certFile, ec); // ignore error
  }
}

Identity
IdentityManagementFixture::addIdentity(const Name& identityName, const KeyParams& params)
{
  auto identity = m_keyChain.createIdentity(identityName, params);
  m_identities.insert(identityName);
  return identity;
}

bool
IdentityManagementFixture::saveIdentityCertificate(const Identity& identity,
                                                   const std::string& filename)
{
  try {
    auto cert = identity.getDefaultKey().getDefaultCertificate();
    return saveCertToFile(cert, filename);
  }
  catch (const security::Pib::Error&) {
    return false;
  }
}

Identity
IdentityManagementFixture::addSubCertificate(const Name& subIdentityName,
                                             const Identity& issuer, const KeyParams& params)
{
  auto subIdentity = addIdentity(subIdentityName, params);

  Certificate request = subIdentity.getDefaultKey().getDefaultCertificate();

  request.setName(request.getKeyName().append("parent").appendVersion());

  SignatureInfo info;
  info.setValidityPeriod(security::ValidityPeriod(time::system_clock::now(),
                                                  time::system_clock::now() + time::days(7300)));

  security::AdditionalDescription description;
  description.set("type", "sub-certificate");
  info.addCustomTlv(description.wireEncode());

  m_keyChain.sign(request, signingByIdentity(issuer).setSignatureInfo(info));
  m_keyChain.setDefaultCertificate(subIdentity.getDefaultKey(), request);

  return subIdentity;
}

Certificate
IdentityManagementFixture::addCertificate(const security::Key& key, const std::string& issuer)
{
  Name certificateName = key.getName();
  certificateName
    .append(issuer)
    .appendVersion();
  Certificate certificate;
  certificate.setName(certificateName);

  // set metainfo
  certificate.setContentType(tlv::ContentType_Key);
  certificate.setFreshnessPeriod(time::hours(1));

  // set content
  certificate.setContent(key.getPublicKey().data(), key.getPublicKey().size());

  // set signature-info
  SignatureInfo info;
  info.setValidityPeriod(security::ValidityPeriod(time::system_clock::now(),
                                                  time::system_clock::now() + time::days(10)));

  m_keyChain.sign(certificate, signingByKey(key).setSignatureInfo(info));
  return certificate;
}

bool
IdentityManagementFixture::saveCertToFile(const Data& obj, const std::string& filename)
{
  m_certFiles.insert(filename);
  try {
    io::save(obj, filename);
    return true;
  }
  catch (const io::Error&) {
    return false;
  }
}

} // namespace tests
} // namespace nac
} // namespace ndn
