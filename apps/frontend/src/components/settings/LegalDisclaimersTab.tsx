/**
 * Legal Disclaimers Tab Component
 *
 * Displays all legal disclaimers, terms, and policies
 * Located in Settings for easy user access
 */

import { useState } from 'react'
import { FileText, ChevronDown, ChevronRight, Download, Shield, Lock, AlertTriangle, Scale } from 'lucide-react'
import toast from 'react-hot-toast'

interface DisclaimerSection {
  id: string
  title: string
  icon: any
  lastUpdated: string
  content: React.ReactNode
}

export default function LegalDisclaimersTab() {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set())

  function toggleSection(sectionId: string) {
    setExpandedSections((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(sectionId)) {
        newSet.delete(sectionId)
      } else {
        newSet.add(sectionId)
      }
      return newSet
    })
  }

  function handleDownloadAll() {
    const content = sections
      .map(
        (section) => `
${section.title.toUpperCase()}
Last Updated: ${section.lastUpdated}
${'='.repeat(80)}

${extractTextContent(section.content)}

`
      )
      .join('\n\n')

    const blob = new Blob([content], { type: 'text/plain;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)

    link.setAttribute('href', url)
    link.setAttribute('download', `ElohimOS-Legal-Disclaimers-${new Date().toISOString().split('T')[0]}.txt`)
    link.style.visibility = 'hidden'

    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    toast.success('Legal documents downloaded')
  }

  function extractTextContent(content: React.ReactNode): string {
    // Simple text extraction for download
    if (typeof content === 'string') return content
    return 'See application for full content'
  }

  const sections: DisclaimerSection[] = [
    {
      id: 'terms',
      title: 'Terms of Service',
      icon: Scale,
      lastUpdated: 'January 1, 2025',
      content: (
        <div className="space-y-4">
          <section>
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
              1. Acceptance of Terms
            </h4>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
              By accessing and using ElohimOS ("the Application"), you accept and agree to be bound
              by these Terms of Service. If you do not agree to these terms, please do not use the
              Application.
            </p>
          </section>

          <section>
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
              2. Use of Service
            </h4>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed mb-2">
              You agree to use the Application only for lawful purposes and in accordance with these
              Terms. You agree not to:
            </p>
            <ul className="text-sm text-gray-700 dark:text-gray-300 space-y-1 ml-4">
              <li>• Use the Application in any way that violates applicable laws or regulations</li>
              <li>• Attempt to gain unauthorized access to any portion of the Application</li>
              <li>• Interfere with or disrupt the Application or servers/networks connected to it</li>
              <li>• Use the Application to transmit malware, viruses, or harmful code</li>
            </ul>
          </section>

          <section>
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
              3. User Accounts and Security
            </h4>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
              You are responsible for maintaining the confidentiality of your account credentials
              and for all activities that occur under your account. You agree to notify us immediately
              of any unauthorized use of your account.
            </p>
          </section>

          <section>
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
              4. Intellectual Property
            </h4>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
              The Application and its original content, features, and functionality are owned by
              ElohimOS and are protected by international copyright, trademark, patent, trade secret,
              and other intellectual property laws.
            </p>
          </section>

          <section>
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
              5. Termination
            </h4>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
              We reserve the right to terminate or suspend your account and access to the Application
              immediately, without prior notice or liability, for any reason, including breach of
              these Terms.
            </p>
          </section>
        </div>
      ),
    },
    {
      id: 'privacy',
      title: 'Privacy Policy',
      icon: Lock,
      lastUpdated: 'January 1, 2025',
      content: (
        <div className="space-y-4">
          <section>
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
              1. Information We Collect
            </h4>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed mb-2">
              We collect information to provide and improve our services:
            </p>
            <ul className="text-sm text-gray-700 dark:text-gray-300 space-y-1 ml-4">
              <li>• Account information (display name, device name)</li>
              <li>• Usage data (features used, timestamps)</li>
              <li>• Device information (device type, operating system)</li>
              <li>• Encrypted vault contents (stored locally with end-to-end encryption)</li>
            </ul>
          </section>

          <section>
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
              2. How We Use Your Information
            </h4>
            <ul className="text-sm text-gray-700 dark:text-gray-300 space-y-1 ml-4">
              <li>• To provide, maintain, and improve the Application</li>
              <li>• To authenticate users and prevent unauthorized access</li>
              <li>• To generate audit logs for security and compliance</li>
              <li>• To respond to support requests and communications</li>
            </ul>
          </section>

          <section>
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
              3. Data Security
            </h4>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
              We implement industry-standard security measures including end-to-end encryption,
              secure key derivation (Argon2), AES-256-GCM encryption, and regular security audits.
              However, no method of transmission over the Internet is 100% secure.
            </p>
          </section>

          <section>
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
              4. Data Retention
            </h4>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
              We retain your data only as long as necessary to provide our services and comply with
              legal obligations. Audit logs are retained for 90 days. You may request deletion of
              your data at any time.
            </p>
          </section>

          <section>
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
              5. Your Rights
            </h4>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
              You have the right to access, correct, or delete your personal data. You may also
              object to or restrict certain processing of your data. Contact us to exercise these
              rights.
            </p>
          </section>
        </div>
      ),
    },
    {
      id: 'medical',
      title: 'Medical Disclaimer',
      icon: AlertTriangle,
      lastUpdated: 'January 1, 2025',
      content: (
        <div className="space-y-4">
          <div className="p-4 bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 dark:border-red-600">
            <p className="text-sm font-semibold text-red-900 dark:text-red-100 mb-2">
              IMPORTANT: This is not medical advice
            </p>
            <p className="text-sm text-red-800 dark:text-red-300">
              If you are experiencing a medical emergency, call 911 immediately.
            </p>
          </div>

          <section>
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
              1. Not a Substitute for Professional Medical Advice
            </h4>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
              The information provided by ElohimOS, including AI-generated health insights, is for
              educational and informational purposes only. It is not intended to be a substitute
              for professional medical advice, diagnosis, or treatment.
            </p>
          </section>

          <section>
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
              2. Always Consult Healthcare Professionals
            </h4>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
              Always seek the advice of your physician or other qualified health provider with any
              questions you may have regarding a medical condition. Never disregard professional
              medical advice or delay in seeking it because of something you have read or received
              through this Application.
            </p>
          </section>

          <section>
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
              3. AI Limitations
            </h4>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
              AI-generated health information is based on patterns in training data and may not
              account for your unique medical history, current conditions, or individual factors.
              AI systems can make errors and should never be used as the sole basis for medical
              decisions.
            </p>
          </section>

          <section>
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
              4. No Doctor-Patient Relationship
            </h4>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
              Use of this Application does not create a doctor-patient relationship. The Application
              and its AI features are not a substitute for professional medical care.
            </p>
          </section>
        </div>
      ),
    },
    {
      id: 'hipaa',
      title: 'HIPAA Compliance Statement',
      icon: Shield,
      lastUpdated: 'January 1, 2025',
      content: (
        <div className="space-y-4">
          <section>
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
              1. HIPAA Compliance Features
            </h4>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed mb-2">
              ElohimOS provides features to help users maintain HIPAA compliance:
            </p>
            <ul className="text-sm text-gray-700 dark:text-gray-300 space-y-1 ml-4">
              <li>• End-to-end encryption for Protected Health Information (PHI)</li>
              <li>• Access controls and role-based permissions</li>
              <li>• Audit logging of all PHI access and modifications</li>
              <li>• Automatic PHI detection and warning systems</li>
              <li>• Secure vault storage for sensitive health data</li>
            </ul>
          </section>

          <section>
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
              2. User Responsibilities
            </h4>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed mb-2">
              While ElohimOS provides HIPAA-compliant features, users and organizations are
              responsible for:
            </p>
            <ul className="text-sm text-gray-700 dark:text-gray-300 space-y-1 ml-4">
              <li>• Properly using encryption features for all PHI</li>
              <li>• Maintaining appropriate access controls</li>
              <li>• Following organizational HIPAA policies and procedures</li>
              <li>• Obtaining proper patient authorization before disclosure</li>
              <li>• Conducting required HIPAA training for staff</li>
            </ul>
          </section>

          <section>
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
              3. Business Associate Agreement
            </h4>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
              Organizations using ElohimOS to store or process PHI may require a Business Associate
              Agreement (BAA). Contact us for information about enterprise compliance agreements.
            </p>
          </section>

          <section>
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
              4. Breach Notification
            </h4>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
              In the event of a security breach affecting PHI, we will notify affected users and
              comply with all HIPAA breach notification requirements within the required timeframes.
            </p>
          </section>
        </div>
      ),
    },
    {
      id: 'liability',
      title: 'Limitation of Liability',
      icon: FileText,
      lastUpdated: 'January 1, 2025',
      content: (
        <div className="space-y-4">
          <section>
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
              1. Disclaimer of Warranties
            </h4>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
              THE APPLICATION IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND,
              WHETHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO IMPLIED WARRANTIES OF
              MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
            </p>
          </section>

          <section>
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
              2. Limitation of Liability
            </h4>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
              TO THE MAXIMUM EXTENT PERMITTED BY LAW, IN NO EVENT SHALL ELOHIMOS, ITS DEVELOPERS,
              OR AFFILIATES BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR
              PUNITIVE DAMAGES, INCLUDING BUT NOT LIMITED TO LOSS OF DATA, LOSS OF PROFITS, OR
              BUSINESS INTERRUPTION, ARISING OUT OF OR RELATED TO YOUR USE OF THE APPLICATION.
            </p>
          </section>

          <section>
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
              3. AI-Generated Content Disclaimer
            </h4>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
              We make no warranties regarding the accuracy, reliability, or completeness of
              AI-generated content. Users assume all risk when relying on AI-generated information
              for any purpose.
            </p>
          </section>

          <section>
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
              4. Indemnification
            </h4>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
              You agree to indemnify and hold harmless ElohimOS, its developers, and affiliates
              from any claims, damages, losses, liabilities, and expenses arising from your use
              of the Application or violation of these Terms.
            </p>
          </section>
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-3 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
        <FileText className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <h4 className="font-semibold text-blue-900 dark:text-blue-100 mb-1">
            Legal Disclaimers & Policies
          </h4>
          <p className="text-sm text-blue-700 dark:text-blue-300">
            Important legal information about your use of ElohimOS. Please read these documents
            carefully to understand your rights and responsibilities.
          </p>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleDownloadAll}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium
                   transition-colors flex items-center gap-2"
        >
          <Download className="w-4 h-4" />
          Download All
        </button>
      </div>

      <div className="space-y-3">
        {sections.map((section) => {
          const isExpanded = expandedSections.has(section.id)
          const Icon = section.icon

          return (
            <div
              key={section.id}
              className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden"
            >
              <button
                onClick={() => toggleSection(section.id)}
                className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                  <div className="text-left">
                    <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                      {section.title}
                    </h3>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      Last updated: {section.lastUpdated}
                    </p>
                  </div>
                </div>
                {isExpanded ? (
                  <ChevronDown className="w-5 h-5 text-gray-400" />
                ) : (
                  <ChevronRight className="w-5 h-5 text-gray-400" />
                )}
              </button>

              {isExpanded && (
                <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/30">
                  {section.content}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          <strong>Questions or Concerns?</strong> If you have questions about these legal documents
          or need clarification, please contact our support team. These terms were last updated on
          January 1, 2025 and may be revised periodically.
        </p>
      </div>
    </div>
  )
}
